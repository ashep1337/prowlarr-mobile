# Build and test the Debian package

This walkthrough targets **Debian 13 (trixie), with systemd**. Start on a test
VM. Stop any manually launched copy using port 8888 before installing the
package, or use a fresh VM for this exercise.

The package uses Debian's Python dependencies. No virtual environment or
`pip install` runs during installation. The existing manual-install workflow
can still use `requirements.txt`; the Debian build uses `debian/control` and
is tested against Debian 13's dependency versions instead.

## 1. Install the build tools

```bash
sudo apt update
sudo apt install build-essential dpkg-dev debhelper dh-python \
  python3-fastapi python3-uvicorn python3-httpx python3-dotenv python3-jinja2 \
  curl
```

`dpkg-dev` supplies the package build command. `debhelper` supplies standard
installation, configuration-file and systemd integration. `dh-python`
handles Python dependency metadata and bytecode maintenance.

If using the prepared source archive:

```bash
tar -xzf prowlarr-mobile-debian-source-0.1.0.tar.gz
cd prowlarr-mobile-0.1.0
```

If applying the patch to an existing Git checkout, start with a clean checkout
of the current `master`, then:

```bash
git switch -c devops/debian-package
git apply --check /path/to/prowlarr-mobile-debian.patch
git apply /path/to/prowlarr-mobile-debian.patch
```

The patch is based on upstream commit `9365685`. If upstream changes again,
resolve any overlapping changes before applying it. Keep your `.env` local;
the package includes only the blank configuration template.

## 2. Understand the packaging files

| File | Purpose |
| --- | --- |
| `debian/control` | Package name, description, supported architecture, build dependencies, and runtime dependencies |
| `debian/changelog` | Package version and release history; the first entry determines the build's version |
| `debian/rules` | Calls standard build helpers, runs tests, and protects the credentials file |
| `debian/source/format` | Declares the source-package format; this walkthrough builds only a binary package |
| `debian/prowlarr-mobile.install` | Lists which source files to copy and where to install them |
| `debian/prowlarr-mobile.service` | The systemd service definition |
| `debian/prowlarr-mobile.sysusers` | Declares the dedicated service user and group |
| `debian/prowlarr-mobile.docs` | Lists documentation included with the package |
| `debian/copyright` | Records ownership and the current licensing status |
| `packaging/prowlarr-mobile` | Launcher installed as `/usr/bin/prowlarr-mobile` |
| `packaging/prowlarr-mobile.env` | Blank default configuration installed under `/etc` |

The service file is shipped in the package, not assembled by a custom
installer. Debhelper generates the maintainer scripts for the service and
service account. `dpkg` tracks the installed files and configuration file.

Two application changes support installation: templates and static assets
are found relative to `main.py`, and the normal launcher runs without the
development auto-reloader. `/health` is a lightweight application check that
does not contact Prowlarr or qBittorrent.

## 3. Build as your normal user

From the project root:

```bash
chmod +x debian/rules packaging/prowlarr-mobile
dpkg-buildpackage -us -uc -b
```

Do **not** run the build with sudo. The package declares
`Rules-Requires-Root: no` and its archive files will still be owned by root
when installed.

- `-b`: build the binary package only.
- `-us -uc`: skip signing source metadata and the changes file for this local
  exercise. A signed APT repository is a later distribution step.

The build runs the homepage, static asset, health and working-directory
smoke tests. Failure stops the build. It writes the outputs one directory
above the source directory:

```text
../prowlarr-mobile_0.1.0-1_all.deb
../prowlarr-mobile_0.1.0-1_amd64.buildinfo
../prowlarr-mobile_0.1.0-1_amd64.changes
```

The `.buildinfo` and `.changes` architecture suffix follows the build machine.
The `.deb` is `all` because it contains architecture-independent application
code; APT supplies the native dependencies for the target machine.

`0.1.0` is the application version and `-1` is the packaging revision. A
packaging-only correction can become `0.1.0-2`.

Inspect the result before installation:

```bash
dpkg-deb --info ../prowlarr-mobile_0.1.0-1_all.deb
dpkg-deb --contents ../prowlarr-mobile_0.1.0-1_all.deb
```

The archive contains an explicit list of application files. It does not
include your Git metadata, local `.env`, virtual environment, or runtime log.

## 4. Install and check the service

```bash
sudo apt install ../prowlarr-mobile_0.1.0-1_all.deb
systemctl status prowlarr-mobile --no-pager
systemctl is-enabled prowlarr-mobile
curl --fail http://127.0.0.1:8888/health
curl --fail --output /dev/null http://127.0.0.1:8888/
```

The health response should be `{"status":"ok"}`. Installation creates a
dedicated, non-login `prowlarr-mobile` account and enables/starts the service
on a normal systemd VM. The process runs as that account, not as root.

| Installed location | Purpose |
| --- | --- |
| `/usr/lib/prowlarr-mobile/` | Application code, templates and static assets |
| `/usr/bin/prowlarr-mobile` | Launcher |
| `/etc/prowlarr-mobile/prowlarr-mobile.env` | Configuration, owned by root with mode `0600` |
| `/usr/lib/systemd/system/prowlarr-mobile.service` | Package-supplied systemd unit |
| `/usr/lib/sysusers.d/prowlarr-mobile.conf` | Service account declaration |
| `/var/lib/prowlarr-mobile/` | Service working/state directory, created by systemd |
| `/usr/share/doc/prowlarr-mobile/` | Packaged documentation |

The systemd manager reads the protected configuration file and passes its
values to the service. Never put real credentials into the packaged template.

## 5. Configure connections and open the interface

```bash
sudoedit /etc/prowlarr-mobile/prowlarr-mobile.env
sudo systemctl restart prowlarr-mobile
journalctl -u prowlarr-mobile -n 50 --no-pager
```

Set the real service URLs and credentials in this installed file. If Prowlarr
or qBittorrent is on another machine, use its reachable address rather than
`127.0.0.1`. Keep passwords on the server.

The package initially listens on `127.0.0.1:8888`. To access it from your
desktop while leaving that default in place, run this on your desktop:

```bash
ssh -L 8890:127.0.0.1:8888 your-user@your-vm
```

Open `http://127.0.0.1:8890` on your desktop while the SSH connection is open.
For access from other devices on a trusted LAN, set `HOST` to the VM's LAN
address (or `0.0.0.0`) in the configuration file, restart, and open
`http://VM-IP:8888`. The current app has no login; internet exposure requires
an authentication layer as a separate feature.

For package lifecycle tests, leave media directories as placeholders. When
you later configure them, the service account needs the appropriate access
to those directories and their parent directories. Permissions previously
granted to your SSH user do not automatically apply to this new account.
The current file-moving feature operates on the configured directory's
contents; use disposable files when testing it.

## 6. Rehearse an upgrade

After editing the installed configuration, record its checksum. This prints
a hash, not the credentials:

```bash
sudo sha256sum /etc/prowlarr-mobile/prowlarr-mobile.env
```

On the build machine, create a new changelog entry and rebuild:

```bash
sudo apt install devscripts
DEBFULLNAME='Alex Shephard' DEBEMAIL='ashep1337@users.noreply.github.com' \
  dch --newversion 0.1.1-1 --distribution unstable 'Rehearse package upgrade.'
dpkg-buildpackage -us -uc -b
```

On the test VM, install the newly built file:

```bash
sudo apt install ./prowlarr-mobile_0.1.1-1_all.deb
dpkg-query -W -f='${Version}\n' prowlarr-mobile
sudo sha256sum /etc/prowlarr-mobile/prowlarr-mobile.env
systemctl is-active prowlarr-mobile
curl --fail http://127.0.0.1:8888/health
```

Adjust the file path if building on the same VM: the file will normally be
`../prowlarr-mobile_0.1.1-1_all.deb`. The version should change, the edited
configuration should retain its checksum, and the service should be running.
If a future release changes the packaged configuration template too, dpkg
may ask whether to keep your version. Keep your settings and merge any new
options deliberately.

## 7. Test removal, reinstall and purge

On the disposable test VM:

```bash
sudo apt remove prowlarr-mobile
sudo test -f /etc/prowlarr-mobile/prowlarr-mobile.env
```

The service should stop and application files should be removed. The
configuration remains. Reinstall the most recently tested `.deb`, then check
the configuration checksum and `/health` again.

```bash
sudo apt install ./prowlarr-mobile_0.1.1-1_all.deb
sudo sha256sum /etc/prowlarr-mobile/prowlarr-mobile.env
curl --fail http://127.0.0.1:8888/health
```

To also remove package-managed configuration:

```bash
sudo apt purge prowlarr-mobile
sudo test ! -e /etc/prowlarr-mobile/prowlarr-mobile.env
```

This package retains the service identity and any state directory created at
runtime. It never removes your download or media directories. Dependencies
installed by APT are managed separately; this exercise does not run autoremove.

## Release checklist

- Run the install, health, upgrade, remove, reinstall and purge exercises on a
  clean Debian 13 VM.
- Choose a project license before the first public redistribution; upstream
  currently has no declared license. `debian/copyright` records that status
  without assigning a new license on the author's behalf.
- Record the supported OS and tested upstream service versions.
- Commit the packaging files, application adjustments and smoke tests in one
  reviewable pull request. Do not commit generated `.deb` files or credentials.
- For a real next release, update `debian/changelog` with the actual changes
  and version. Tag the corresponding source commit and attach the built
  `.deb` and checksum to its GitHub Release.
- APT repository publication, release automation, a browser setup wizard,
  application login and broader service-integration tests can follow in
  separate changes.

References:

- https://www.debian.org/doc/manuals/maint-guide/
- https://manpages.debian.org/trixie/debhelper/dh_installsystemd.1.en.html
- https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html
