##########################################################################
# File:         Letter.py                                                #
# Purpose:      Automatically send batch of mails                        #
# Last changed: 2015/06/21                                               #
# Author:       zhuang-jia-xu                                            #
# Edited:                                                                #
# Copyleft:     (ɔ)NTUEE                                                 #
##########################################################################
from cerberus import Validator
from email_validator import validate_email, caching_resolver

import os
import csv
import yaml
import re
import logging
from typing import List
from pathlib import Path, PurePath
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from string import Template

from .utils import *

__all__ = ["Letter"]

letter_config_schema = {
    "subject": {"type": "string", "required": True},
    "from": {"type": "string"},
    "recipientTitle": {"type": "string"},
    "lastNameOnly": {"type": "boolean"},
    "cc": {"type": "list"},
    "bcc": {"type": "list"},
    "bccToSender": {"type": "boolean"},
}

v = Validator(letter_config_schema)

RESERVED_FIELDS = ("email", "cc", "bcc")
REQUIRED_FIELDS = ("email", "name")

class Letter:
    paths: dict = None
    config: dict = None
    csv: List = None
    email_addrs: List = None
    emails: List = None

    def __init__(self, letter_path: str, sender_name: str, *, test_mode: bool = False):
        if not self.validate_letter_dir(letter_path, verbose=True):
            richError(f"{letter_path} is not a valid letter directory")

        self.paths = self.get_paths(letter_path)

        self.config = {
            **self.__load_letter_config(),
            "sender_name": sender_name,
            "attachments": [],
        }

        if Path(self.paths["attachments"]).is_dir():
            attachments = list(
                filter(lambda a: a[0] != ".", os.listdir(self.paths["attachments"]))
            )
            if len(attachments) > 0:
                self.config["attachments"] = [
                    Path(self.paths["attachments"]) / a for a in attachments
                ]

        self.csv = self.__load_recipients()
        self.email_addrs = [row["email"] for row in self.csv]
        self.emails = self.__generate_emails(test_mode=test_mode)

    def set_from_addr(self, from_addr: str):
        for email in self.emails:
            email["From"] = formataddr((self.config["from"], from_addr))

            if "bcc" in self.config:
                if "bccToSender" in self.config and self.config["bccToSender"]:
                    bccs = [*self.config["bcc"], from_addr]
                    email["Bcc"] = ",".join(bccs)
                else:
                    email["Bcc"] = ",".join(self.config["bcc"])
            elif "bccToSender" in self.config and self.config["bccToSender"]:
                email["Bcc"] = from_addr

    def __load_letter_config(self):
        path = self.paths["config"]
        if not Path(path).is_file():
            logging.error(f"{path} is not a file")
            richError(
                f"failed to load letter config at {path}, please enter a valid letter path"
            )

        letter_config = self.load_file(path)

        if not self.validate_letter_config(letter_config, verbose=True):
            logging.error(f"{path} is not a valid letter config")
            richError(
                f"failed to load letter config at {path}, please enter a valid letter path"
            )

        if "cc" in letter_config:
            letter_config["cc"] = letter_config["cc"] = complete_school_email(
                letter_config["cc"]
            )
        if "bcc" in letter_config:
            letter_config["bcc"] = complete_school_email(letter_config["bcc"])

        return letter_config

    def __load_recipients(self):
        """load recipients from csv file"""
        path = self.paths["recipients"]
        recipients = self.load_file(path)

        is_valid = self.validate_recipients(recipients, verbose=True)

        if not is_valid:
            logging.error(f"letter csv: {Path(self.paths['recipients']).read_text()}")
            richError(f"failed to load recipients from {self.paths['recipients']}")
            return

        return recipients

    def __generate_emails(self, *, test_mode: bool = False):
        """generate emails from csv file"""
        emails = []

        email_template = Path(self.paths["content"]).read_text(encoding="utf-8")

        if not self.validate_email_content(email_template, self.csv[0].keys(), verbose=True):
            return
        
        email_template = Template(email_template)

        # create attachments
        mime_attachments = []
        for attachment in self.config["attachments"]:
            with open(attachment, "rb") as f:
                mime_attachment = MIMEApplication(
                    f.read(), Name=os.path.basename(attachment)
                )

            mime_attachment[
                "Content-Disposition"
            ] = f"attachment; filename={os.path.basename(attachment)}"

            mime_attachments.append(mime_attachment)

        for recipient in self.csv:
            email = self.__generate_email(recipient, email_template, mime_attachments)
            emails.append(email)
            if test_mode:
                break
        return emails

    def __generate_email(
        self,
        recipient: dict,
        email_template: Template,
        mime_attachments: List[MIMEApplication],
    ):
        """generate email from recipient"""

        email = MIMEMultipart()
        email["Date"] = formatdate(localtime=True)

        email["Subject"] = self.config["subject"]

        email["To"] = recipient["email"]

        cc_list = []
        if "cc" in self.config:
            cc_list += self.config["cc"]
        if "cc" in recipient:
            cc_list += [recipient["cc"]]
        if len(cc_list) > 0: 
            email["Cc"] = ",".join(cc_list)

        bcc_list = []
        if "bcc" in self.config:
            bcc_list += self.config["bcc"]
        if "bcc" in recipient:
            bcc_list += [recipient["bcc"]]
        if len(bcc_list) > 0:
            email["Bcc"] = ",".join(bcc_list)

        if "recipientTitle" in self.config:
            if "lastNameOnly" in self.config and self.config["lastNameOnly"]:
                # only supports chinese names
                recipient["name"] = recipient["name"][0]
            recipient["name"] = recipient["name"] + self.config["recipientTitle"]

        email.attach(
            MIMEText(
                email_template.substitute(
                    {**recipient, "sender": self.config["sender_name"]}
                ),
                "html",
            )
        )

        for mime_attachment in mime_attachments:
            email.attach(mime_attachment)

        return email

    def __iter__(self):
        return iter(self.emails)

    def __len__(self):
        return len(self.emails)

    @classmethod
    def load_file(cls, file_path: str):
        """load letter from config"""
        file_name = PurePath(file_path).name
        if file_name == "content.html":
            return Path(file_path).read_text(encoding="utf-8")

        elif file_name == "config.yml" or file_name == "config.yaml":
            with open(file_path, encoding="utf-8") as f:
                letter_config = yaml.load(f, Loader=yaml.FullLoader)

            return letter_config

        elif file_name == "recipients.csv":
            with open(file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                recipients = [row for row in reader]

                stripped_recipients = []
                for row in recipients:
                    temp_row = {}
                    for key, value in row.items():
                        temp_row[key.strip()] = value.strip()

                    if "email" in temp_row:
                        temp_row["email"] = complete_school_email(temp_row["email"].lower())
                    if "cc" in temp_row:
                        temp_row["cc"] = complete_school_email(temp_row["cc"].lower())
                    if "bcc" in temp_row:
                        temp_row["bcc"] = complete_school_email(temp_row["bcc"].lower())
                    
                    stripped_recipients.append(temp_row)

            return stripped_recipients

        else:
            return None

    @classmethod
    def check_letter(cls, letter_path: str, verbose=False) -> bool:
        """check letter"""
        is_valid = True

        is_valid &= cls.validate_letter_dir(letter_path, verbose=verbose)
        if not is_valid:
            return False

        paths = cls.get_paths(letter_path)

        config_file = cls.load_file(paths["config"])
        content_file = cls.load_file(paths["content"])
        recipients_file = cls.load_file(paths["recipients"])

        is_valid &= cls.validate_letter_config(config_file, verbose=verbose)

        is_valid &= cls.validate_recipients(recipients_file, verbose=verbose)
        if not is_valid:
            return False

        is_valid &= cls.validate_email_content(
            content_file, recipients_file[0], verbose=verbose
        )

        return is_valid

    @classmethod
    def validate_letter_dir(cls, letter_path: str, verbose=False) -> bool:
        paths = cls.get_paths(letter_path)

        is_valid = True
        for key, path in paths.items():
            if not path.exists():
                if verbose:
                    logging.error(f"letter: {path} not found")
                    richError(f"letter {key} not found at {path}", terminate=False)
                    is_valid = False
                else:
                    return False
            if key == "attachments":
                if not path.is_dir():
                    if verbose:
                        richError(f"{path} should be a dir", terminate=False)
                        is_valid = False
                    else:
                        return False
            else:
                if not path.is_file():
                    if verbose:
                        richError(f"{path} should be a file", terminate=False)
                        is_valid = False
                    else:
                        return False

        return is_valid

    @classmethod
    def validate_letter_config(cls, letter_config: dict, verbose=False) -> bool:
        is_valid = v.validate(letter_config)
        if verbose:
            parse_validation_error(v._errors)
        return is_valid

    @classmethod
    def validate_recipients(cls, stripped_recipients: list, verbose=False) -> bool:
        """validate recipients"""

        is_valid = True

        for required in REQUIRED_FIELDS:
            if required not in stripped_recipients[0]:
                if verbose:
                    logging.error(
                        f"{required} is a required field in the csv file, but not found"
                    )
                    richError(
                        f"{required} is a required field in the csv file, but not found",
                        terminate=False,
                    )
                    is_valid = False
                else:
                    return False
                    
        for row in stripped_recipients:
            for i, (key, value) in enumerate(row.items()):
                if key is None:
                    if verbose:
                        logging.error(f"too many fields at row {i} in recipients.csv")
                        richError(
                            f"too many fields at row {i} in recipients.csv",
                            terminate=False,
                        )
                        is_valid = False
                        continue
                    else:
                        return False

                if key in REQUIRED_FIELDS and value == "":
                    if verbose:
                        logging.error(
                            f"{key} cannot be empty, recipients.csv has no {key} at row {i}"
                        )
                        richError(
                            f"{key} cannot be empty, recipients.csv has no {key} at row {i}",
                            terminate=False,
                        )
                        is_valid = False
                    else:
                        return False

        resolver = caching_resolver()

        for i, row in enumerate(stripped_recipients):
            row["email"] = complete_school_email(row["email"].lower())
            try:
                validate_email(row["email"], dns_resolver=resolver)
            except:
                if verbose:
                    logging.error(
                        f"recipients.csv has invalid email: {row['email']}, at row {i}"
                    )
                    richError(
                        f"invalid email {row['email']} detected at row {i} in recipients.csv",
                        terminate=False,
                    )
                    is_valid = False
                else:
                    return False

        return is_valid

    @classmethod
    def validate_email_content(
        cls, email_template: str, csv_indexes: list, verbose=False
    ) -> bool:
        """validate email content"""
        template_fields = re.findall(r"\$([_a-z][_a-z0-9]*)", email_template, re.M)
        is_valid = True

        for reserved in RESERVED_FIELDS:
            if reserved in template_fields:
                if verbose:
                    logging.error(
                        f"{reserved} is a reserved field, it cannot be used in email template"
                    )
                    richError(
                        f"{reserved} is a reserved field, it cannot be used in email template",
                        terminate=False,
                    )
                    is_valid = False
                else:
                    return False

        csv_indexes = [f.strip() for f in template_fields] + ["sender"]
        for field in template_fields:
            if field not in csv_indexes:
                if verbose:
                    logging.error(f"letter template has field '{field}', but is not found in csv")
                    richError(
                        f"letter template has field '{field}', but is not found in csv",
                        terminate=False,
                    )
                    is_valid = False
                else:
                    return False

        return is_valid

    @classmethod
    def get_paths(self, letter_path: str) -> list:
        """get paths to different part of letters"""
        letter_root_path = Path(letter_path)

        paths = {
            "content": letter_root_path / "content.html",
            "config": letter_root_path / "config.yml",
            "attachments": letter_root_path / "attachments",
            "recipients": letter_root_path / "recipients.csv",
        }

        return paths
