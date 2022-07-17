# `ntuee-mailer`

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

- `check`: check wether a directory is a valid letter
- `config`: configure the auto mailer a valid config file
- `new`: create a new letter from template
- `send`: send emails to a list of recipients as

## `ntuee-mailer check`

check wether a directory is a valid letter

a letter folder should be structured as follows:

letter

├── attachments
│ ├── ...
│ └── ...
├── config.yml
├── content.html
└── recipients.csv

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

**Usage**:

```console
$ ntuee-mailer config [OPTIONS]
```

**Options**:

- `-f, --file TEXT`: Path to new config file whose content will be copied to config.ini
- `-r, --reset`: Reset config.ini to default [default: False]
- `-s, --show`: Show config.ini [default: False]
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
- `-c, --config FILE`: Path to config.ini [default: /home/madmax/.config/ntuee_mailer-mailer/config.ini]
- `-q, --quiet`: Quiet mode: less output [default: False]
- `-d, --debug INTEGER RANGE`: Debug level [default: 0]
- `--help`: Show this message and exit.
