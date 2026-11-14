# Debian package validation

Package: `prowlarr-mobile_0.1.0-1_all.deb`

Source baseline: upstream `master` at `9365685`, plus the included packaging
changes. The source bundle and patch contain those changes; no commits were
pushed to GitHub.

## Checks completed

The package was built using `dpkg-buildpackage -us -uc -b` in an isolated
Debian 13 filesystem with its build dependencies installed. The build used
Debian-packaged Python dependencies, including FastAPI 0.115.11, Uvicorn
0.32.0 and HTTPX 0.28.1.

| Check | Result |
| --- | --- |
| Build dependency checks and binary package build | Passed |
| Homepage and linked static assets | Passed |
| Health endpoint without Prowlarr/qBittorrent | Passed |
| Application import outside its source directory | Passed |
| Package installation using dpkg | Passed |
| Dedicated service user and group creation | Passed |
| Systemd unit enabled on installation | Passed |
| `systemd-analyze verify` of installed unit | Passed |
| Installed configuration mode `0600` | Passed |
| Installed launcher serves homepage, assets and health from `/tmp` | Passed |
| Upgrade from `0.1.0-1` to a test build `0.1.0-2` | Passed |
| Modified configuration retained across upgrade | Passed |
| Removal retains configuration and disposable media sentinel | Passed |
| Reinstallation retains configuration and serves the app | Passed |
| Purge removes package configuration and retains media sentinel | Passed |

## Final VM checks

The isolated environment was not booted with systemd as PID 1. Service
startup at boot, process execution as the dedicated service user, automatic
restart and journal integration still need verification on a booted Debian
13 VM. The walkthrough supplies the commands to perform these checks.

The installed launcher was exercised directly during the package lifecycle
tests. No real Prowlarr/qBittorrent services, credentials or media were used.
Search, torrent controls, file movement, reverse proxying and internet
authentication are outside this packaging validation.
