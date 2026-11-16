# aur-zuse-bin

[![AUR package](https://img.shields.io/aur/version/zuse-bin)](https://aur.archlinux.org/packages/zuse-bin)
[![Update & Sync](https://github.com/minpeter/aur-zuse-bin/actions/workflows/sync.yml/badge.svg)](https://github.com/minpeter/aur-zuse-bin/actions/workflows/sync.yml)

Arch Linux AUR packaging repository for [Zuse](https://github.com/opcodehq/zuse),
the native desktop and browser control plane for coding agents.

- **AUR Package:** [`zuse-bin`](https://aur.archlinux.org/packages/zuse-bin)
- **Official Upstream:** [opcodehq/zuse](https://github.com/opcodehq/zuse)

---

## Installation

Using an AUR helper like `yay` or `paru`:

```bash
yay -S zuse-bin
# or
paru -S zuse-bin
```

Or manually with `makepkg`:

```bash
git clone https://aur.archlinux.org/zuse-bin.git
cd zuse-bin
makepkg -si
```

The package installs the official prebuilt Linux binaries under `/usr/lib/zuse` and
launchers in `/usr/bin` (`zuse`, `zuse-server`, `zuse-relay`).

## Notes

- **Updates stay with pacman.** The launcher exports `ZUSE_AUTO_UPDATE=0`, so
  Zuse's built-in updater only reports new releases instead of downloading and
  installing them behind the package manager's back. Set `ZUSE_AUTO_UPDATE=1`
  yourself if you want the upstream self-updater.
- **Name collision.** AUR's [`zuse-git`](https://aur.archlinux.org/packages/zuse-git)
  is an unrelated terminal IRC client that also installs `/usr/bin/zuse`, so
  this package declares a conflict with it.
- **Runtime requirements.** Zuse needs WebKitGTK 4.1, a working Vulkan driver
  and X11 or Wayland. The package pulls the library dependencies; the GPU
  driver comes from your system.

## Automation

This repository automatically tracks upstream GitHub releases every 6 hours via
GitHub Actions. Each run:

1. Fails immediately if the `AUR_SSH_PRIVATE_KEY` secret is missing
2. Checks the latest stable upstream release and, if it changed, updates
   `pkgver` and both architecture checksums in `PKGBUILD`
3. Compares `PKGBUILD` with the one currently on the
   [AUR](https://aur.archlinux.org/packages/zuse-bin); any difference (new
   release, manual change, or a previously failed AUR push) triggers a deploy
4. Builds the package with `makepkg --syncdeps` in an `archlinux:base-devel`
   container (`scripts/arch-build.sh`) and regenerates `.SRCINFO`; a build
   failure stops the run before anything is published
5. Pushes to the AUR first, then commits `PKGBUILD` and `.SRCINFO` to GitHub

`PKGBUILD` on GitHub is the source of truth: direct edits on the AUR are
overwritten by the next run.
