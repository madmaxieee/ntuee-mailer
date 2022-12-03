from rich import print
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    BarColumn,
)
from rich.prompt import Prompt
from cerberus import Validator

import time
import os
import re
import logging
from typing import List
from configparser import ConfigParser
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
import poplib
from email.parser import Parser as EmailParser

from .utils import *
from .globals import *
from .Letter import Letter

__all__ = ["AutoMailer"]

auto_mailer_config_schema = {
    "account": {
        "type": "dict",
        "schema": {
            "name": {"type": "string", "required": True},
            "userid": {"type": "string"},
        },
    },
    "smtp": {
        "require_all": True,
        "type": "dict",
        "schema": {
            "host": {"type": "string"},
            "port": {"type": "integer", "coerce": int},
            "timeout": {"type": "integer", "coerce": int},
        },
    },
    "pop3": {
        "require_all": True,
        "type": "dict",
        "schema": {
            "host": {"type": "string"},
            "port": {"type": "integer", "coerce": int},
            "timeout": {"type": "integer", "coerce": int},
        },
    },
}
v = Validator(auto_mailer_config_schema)

email_re = re.compile("[a-z0-9-_\.]+@[a-z0-9-\.]+\.[a-z\.]{2,5}")


class AutoMailer:
    verbose: bool = True
    SMTPserver: smtplib.SMTP_SSL = None
    config: dict = None
    total_count: int = 0
    success_count: int = 0
    email_addrs: List[str] = []
    userid: str = None
    password: str = None

    def __init__(self, config: dict = None, quiet: bool = False) -> None:
        self.config = config
        self.verbose = not quiet
        self.SMTPserver = self.__createSMTPServer()

    def login(self) -> None:
        """login to SMTP server"""
        for i in range(3):
            try:
                self.SMTPserver.login(*self.__get_login_info())
            except KeyboardInterrupt:
                exit(1)
            except:
                logging.info(f"Login failed {i+1} times")
                richError(
                    "\nLogin failed, please try again", prefix="", terminate=False
                )
                time.sleep(1)
                continue
            richSuccess("Login success")
            return

        richError("Too many failed login attempts", prefix="")

    def __get_login_info(self) -> dict:
        """get login info"""
        print("\n[blue]\[User login]")

        if "userid" in self.config["account"]:
            userid = Prompt.ask(
                "[blue]Username[/blue] saved user id:",
                default=self.config["account"]["userid"],
            )
        else:
            userid = Prompt.ask("[blue]Username[/blue] (e.g. b09901000)",)
            userid = userid.strip()

            save_id = Confirm.ask("[blue]remember this userid?[/blue]", default=True)
            if save_id:
                new_config = self.config.copy()
                new_config["account"] = self.config["account"].copy()
                new_config["account"]["userid"] = userid
                self.save_config(new_config)

        password = Prompt.ask("[blue]password", password=True)

        print("\n")

        self.userid = userid
        self.password = password
        return userid, password

    def send_emails(
        self, letter: Letter, *, test_mode: bool = False, dry: bool = False
    ) -> None:
        """send emails"""
        if self.verbose:
            print("-" * 50)
            print(Path(letter.paths["content"]).read_text(encoding="utf-8"))
            print("-" * 50)
            if not countdownConfirm(
                "Are you sure to send emails with the content above?",
                default=False,
                countdown=3,
            ):
                logging.info("User cancelled on checking content")
                richError("Canceled", prefix="")

        if not Confirm.ask(
            f"""
You are about to send email{'s' if len(letter) > 1 else ''} 
with your name set to [blue]'{self.config['account']['name']}'[/blue]
to [blue]{len(letter)}[/blue] recipients? (please use test mode before you send emails)\n
Do you want to continue?""",
            default=False,
        ):
            logging.info("User cancelled on sending emails")
            richError("Canceled", prefix="")

        if self.SMTPserver is None:
            logging.info("SMTP server is not connected, please connect first")
            richError("SMTP server is not connected, please connect first")

        self.email_addrs += letter.email_addrs

        letter.set_from_addr(complete_school_email(self.userid))

        progress = Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.completed} of {task.total:.0f}",
            "•",
            TimeRemainingColumn(),
        )

        with progress:
            logging.info(f"Sending {len(letter)} emails")
            for email in progress.track(letter, description="Sending emails..."):
                self.__server_rest(progress)

                if not dry:
                    success = self.send_email(email, test_mode=test_mode)
                else:
                    success = True

                if success:
                    if self.verbose:
                        progress.print(
                            f"[green]successfully sent email to {(complete_school_email(self.userid)+' (yourself)') if test_mode else email['To']}"
                        )
                else:
                    progress.print(
                        f"[red]failed to send email to {(complete_school_email(self.userid)+' (yourself)') if test_mode else email['To']}"
                    )

            if dry:
                print("[red]This is a dry run, no emails were actually sent")

    def send_email(self, email: MIMEMultipart, *, test_mode: bool = False) -> None:
        """send email"""
        if self.SMTPserver is None:
            richError("SMTP server is not connected, please connect first")

        self.total_count += 1

        if test_mode:
            toaddrs = complete_school_email(self.userid)
            ccaddrs = ""
            bccaddrs = ""
        else:
            toaddrs = email["To"].split(",")
            ccaddrs = email["Cc"].split(",") if email["Cc"] is not None else []
            bccaddrs = email["Bcc"].split(",") if email["Bcc"] is not None else []

        try:
            self.SMTPserver.sendmail(
                email["From"], toaddrs + ccaddrs + bccaddrs, email.as_string(),
            )
        except Exception as e:
            logging.error(e)
            logging.error(f"Failed to send email to {email['To']}")
            return False

        logging.info(f"Sent email {toaddrs}")

        self.success_count += 1
        return True

    def check_bounce_backs(self) -> None:
        """show help message if emails are bounced back, this usually happens when trying to email a wrong school email address"""
        if self.total_count == 0:
            print("No emails were sent, nothing to check")
            return

        logging.info("Checking bounce backs")
        progress = Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        )
        with progress:
            progress.add_task(description="checking for bounce-backs...", total=None)
            time.sleep(5)  # wait for bounce back

            try:
                # connect to pop3 server
                pop3 = poplib.POP3_SSL(
                    host=self.config["pop3"]["host"],
                    port=self.config["pop3"]["port"],
                    timeout=self.config["pop3"]["timeout"],
                )
                pop3.user(self.userid)
                pop3.pass_(self.password)
            except Exception as e:
                logging.error(e)
                logging.error("Failed to connect to pop3 server")
                progress.print("[red]Failed to connect to pop3 server")
                return 0

            progress.print("Connected to POP3 server")
            logging.info("Connected to POP3 server")
            # retrieve last n emails
            _, mails, _ = pop3.list()
            emails = [
                pop3.retr(i)[1]
                for i in range(len(mails), len(mails) - len(self.email_addrs), -1)
            ]
            pop3.quit()

            email_contents = []
            # Concat message pieces:
            for msg in emails:
                # some chinese character may not be able to parse,
                # however, we only care about the bounce back notifications,
                # which are always in English
                try:
                    email_contents.append(b"\r\n".join(msg).decode("utf-8"))
                except:
                    continue

            # Parse message into an email object:
            email_contents = [
                EmailParser().parsestr(content, headersonly=True)
                for content in email_contents
            ]

            bounced_list = []

            for content in email_contents:
                if not re.match(
                    "(Delivery Status Notification)|(Undelivered Mail Returned to Sender)",
                    content["subject"],
                ):
                    continue

                # match for email addresses
                addr = email_re.search(content.get_payload()).group()
                bounced_list.append(addr)

            bounced_list = list(filter(lambda x: x in self.email_addrs, bounced_list))

            if len(bounced_list) > 0:
                progress.print(
                    "[red]Emails sent to these addresses are bounced back (failed):"
                )
                for address in bounced_list:
                    progress.print(f"\t{address},")
                progress.print("[red]Please check these emails.")
            else:
                progress.print(
                    "[green]No bounce-backs found, all emails are delivered successfully",
                )

        self.success_count -= len(bounced_list)

    def __server_rest(self, progress):
        """for bypassing email server limitation"""

        def rest(seconds):
            progress.print(f"[blue]resting for {seconds} seconds...")
            time.sleep(seconds)

        if self.total_count % 260 == 0 and self.total_count > 0:
            rest(50)
        elif self.total_count % 130 == 0 and self.total_count > 0:
            rest(30)
        elif self.total_count % 10 == 0 and self.total_count > 0:
            rest(10)

    def __createSMTPServer(self) -> smtplib.SMTP_SSL:
        """create SMTP server"""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Connecting to SMTP Server...", total=None)

            time.sleep(1)

            try:
                server = smtplib.SMTP_SSL(
                    host=self.config["smtp"]["host"],
                    port=self.config["smtp"]["port"],
                    timeout=self.config["smtp"]["timeout"],
                )
            except Exception as e:
                logging.critical(e)
                logging.critical("Failed to connect to SMTP server")
                progress.print("[red]Failed to connect to SMTP server")
                exit(1)

            if server.has_extn("STARTTLS"):
                server.starttls()

            server.ehlo_or_helo_if_needed()

        logging.info("Connected to SMTP server")
        richSuccess("SMTP server connected")

        return server

    @classmethod
    def load_mailer_config(cls, config_path: str) -> dict:
        """load auto mailer configuration from config.ini"""
        config_path = Path(config_path)
        automailer_config = ConfigParser()
        if not os.path.exists(config_path):
            richError(f"{config_path} not found")

        automailer_config.read({config_path}, encoding="utf-8")

        sections = automailer_config.sections()

        config = {}

        for section in sections:
            options = automailer_config.options(section)
            temp_dict = {}
            for option in options:
                temp_dict[option] = automailer_config.get(section, option)

            config[section] = temp_dict

        if cls.validate_config(config, verbose=True):
            config = v.document.copy()
            if config["account"]["name"] == "":
                config["account"]["name"] = Prompt.ask(
                    'Your name is currently set to [blue]""[/blue], Please enter your name',
                )
            return config
        else:
            logging.critical(
                f"mailer config validation failed, please check {config_path}"
            )
            logging.critical(config)
            richError(f"mailer config validation failed, please check {config_path}",)

    @classmethod
    def validate_config(cls, config: dict, verbose=False) -> bool:
        """validate config"""
        if v.validate(config):
            return True
        else:
            if verbose:
                parse_validation_error(v._errors)
            return False

    @classmethod
    def save_config(cls, config: dict):
        if not cls.validate_config(config):
            return False

        new_config_parser = ConfigParser()

        for section, vals in config.items():
            new_config_parser[section] = vals

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            new_config_parser.write(f)

        return True


if __name__ == "__main__":
    auto_mailer_config = AutoMailer.load_mailer_config("config.ini")
    auto_mailer = AutoMailer(auto_mailer_config)
    emails = Letter(
        "letters/test",
        auto_mailer_config["account"]["name"],
        complete_school_email(auto_mailer_config["account"]["userid"]),
    )
    auto_mailer.connect()
    auto_mailer.send_emails(emails)
    auto_mailer.check_bounce_backs()
