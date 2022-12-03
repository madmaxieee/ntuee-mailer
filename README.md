# `ntuee-mailer`

This is a simple mailer for NTU students to send letters in batches.

**Installation**

```bash
$ pip install ntuee-mailer
```

**Usage**:

```bash
$ ntuee-mailer [OPTIONS] COMMAND [ARGS]...
```

**Options**:

- `--install-completion`: Install completion for the current shell.
- `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
- `--help`: Show this message and exit.

**Commands**:

- `check`: check wether a directory is a valid letter a...
- `config`: configure the auto mailer a valid config file...
- `new`: create a new letter from template
- `send`: send emails to a list of recipients as...

## `ntuee-mailer check`

check wether a directory is a valid letter

a letter folder should be structured as follows:

```
letter_name
├── attachments
│ ├── ...
│ └── ...
├── config.yml
├── content.html
└── recipients.csv
```

**Usage**:

```console
$ ntuee-mailer check [OPTIONS] LETTER_PATH
```

**Arguments**:

- `LETTER_PATH`: Path to letter directory [required]

**Options**:

- `--help`: Show this message and exit.

## `ntuee-mailer config`

configure the auto mailer

a valid config file should have the following structure:

```
[smtp]
host=smtps.ntu.edu.tw
port=465
timeout=5
[pop3]
host=msa.ntu.edu.tw
port=995
timeout=5
[account]
name=John Doe
```

**Usage**:

```console
$ ntuee-mailer config [OPTIONS]
```

**Options**:

- `-f, --file TEXT`: Path to new config file whose content will be copied to config.ini
- `-r, --reset`: Reset config.ini to default [default: False]
- `-l, --list`: list current config [default: False]
- `--help`: Show this message and exit.

## `ntuee-mailer new`

create a new letter from template

**Usage**:

```console
$ ntuee-mailer new [OPTIONS] LETTER_NAME
```

**Arguments**:

- `LETTER_NAME`: Name of letter [required]

**Options**:

- `--help`: Show this message and exit.

## `ntuee-mailer send`

send emails to a list of recipients as configured in your letter

**Usage**:

```console
$ ntuee-mailer send [OPTIONS] [LETTER_PATH]
```

**Arguments**:

- `[LETTER_PATH]`: Path to letter

**Options**:

- `-t, --test`: Test mode: send mail to yourself [default: False]
- `-c, --config FILE`: Path to config.ini [default: /home/madmax/.config/ntuee-mailer/config.ini]
- `-q, --quiet`: Quiet mode: less output [default: False]
- `-d, --debug INTEGER RANGE`: Debug level [default: 0]
- `--help`: Show this message and exit.

## `ntuee-mailer test`

**Usage**:

```console
$ ntuee-mailer test [OPTIONS]
```

**Options**:

- `--help`: Show this message and exit.

## mail format

a letter folder should be structured as follows:
```
letter_name
├── attachments
│ ├── ...
│ └── ...
├── config.yml
├── content.html
└── recipients.csv
```

### content.html
The content of the email. `$<pattern>` would be replaced by the corresponding field defined in `recipients.csv`

### recipients.csv
Stores the data related to recipients. The value of "name" field is will be used to replace `$name` in `content.html`, whose behavior can be modified in `config.yml`. The "email" field stores the recipients email. The emails will be CCed and BCCed to the emails in "cc" and "bcc" field. One recipients may have several CC and BCCs, emails should be separated with spaces. "email", "cc" and "bcc" are reserved fields, they cannot be used in html pattern, any additional field will be replaced in the html. "name" and "email" fields are required

### config.yml
Configuration of each email. "subjects" defines subject, "from" defines the name recipients see in their email client. "recipientTitle" and "lastNameOnly" modifies the behavior of `$name` in `content.html`.

### attachments
The attachment directory. Any file placed in this folder will be attached to the email. Any file with name started with '.' will be ignored, i.e. .git, .DS_STORE.
