# Jenny92 maintained PortMaster release

This branch follows official PortMaster stable releases and adds the minimum support
required for MiniLoong. It is consumed by Port App Manager only on MiniLoong; supported
official devices continue to download official PortMaster releases.

The upstream project documentation in the repository root remains unchanged except for
the branch notice. This file is the maintenance source of truth for the fork.

## Change boundaries

Changes are kept in three reviewable layers:

### Intended for upstream

- Current LoongOS device detection, platform metadata and standard PortMaster launch
  behavior.
- The generic fix for inspecting the selected `runtimes.zip` archive.
- Tests that prove those behaviors with mock device roots.

This layer must not contain Jenny92 release URLs, Port App Manager integration or fork
CI behavior. It can be proposed upstream independently of the other two layers.

### Legacy MiniLoong compatibility

- LoongOS 1.3 device detection and `/mnt/sdcard/roms/ports` paths.
- The legacy Python squashfs launcher required by that firmware.

This layer is deliberately separate because it is larger and may not be accepted
upstream. Current LoongOS detection always wins when both current and legacy markers
exist.

### Fork only

- The weekly official-stable follower workflow.
- Jenny92 stable release building and self-update routing.
- BusyBox-compatible extraction and completeness checks for the bundled CJK fonts.
- Cross-repository validation of the built archive with Port App Manager's current
  Rust installer and generated device configuration.
- This maintenance documentation and source configuration.

Do not include the fork-only layer in an upstream pull request.

## Published assets

Each maintained release uses the exact official stable version and publishes only:

| Asset | Purpose |
| --- | --- |
| `PortMaster.zip` | PortMaster managed core with MiniLoong support and Jenny92 stable self-update routing. |
| `version.json` | Standard `stable`/`beta`/`alpha` records, exact archive URL and archive MD5. All three currently resolve to the validated stable. |
| `SHA256SUMS` | Additional CI/release integrity record for `version.json` and `PortMaster.zip`. |

The archive excludes `libs`, `config`, `themes`, logs and caches; Port App Manager's
in-process Rust installer preserves those live directories while installing the built
archive through each supported MiniLoong profile.

The packaged PortMaster self-update URL points to Jenny92 stable releases so MiniLoong
support cannot be overwritten by an official self-update. Runtime metadata, port
packages, images and themes remain on their official PortMaster sources.
Maintained builds add `Maintainer: Jenny92` to the main-menu system status so they
cannot be confused with an official upstream build.

The GUI keeps PortMaster's official update-channel behavior and field names. The
installed default is `stable`, but `PORTMASTER_RELEASE_VALUES` still exposes `stable`,
`beta` and `alpha`; the generated `version.json` currently gives all three the same
stable version, URL and MD5. This prevents a channel switch from leaving the maintained
release while allowing future beta/alpha support to be enabled entirely in release
generation without changing the GUI update client.

Official releases also publish `muos.portmaster.zip`, `trimui.portmaster.zip` and
`retrodeck.portmaster.zip`. Those are initial-distribution layout archives: they wrap
the generic core under firmware-specific directories and frontend launch files.
PortMaster self-update never downloads them; it always follows the selected
`version.json` record to `PortMaster.zip`. This fork does not publish a
`loong.portmaster.zip` because Port App Manager already performs MiniLoong path and
frontend installation from the generic archive. Add such an asset only when an external
LoongOS firmware installer has a concrete filename/layout contract for it.

## Stable follower workflow

`.github/workflows/follow-official-stable.yaml` runs weekly and can also be dispatched
manually.

For an explicit manual entry in GitHub Actions, run `Build MiniLoong Package`, select
`validate` to perform all checks without publishing, or select `publish` to validate,
update the maintained branch and publish the release. That small dispatcher calls the
same stable-follower workflow, so scheduled and manual releases cannot drift apart.

1. Read `stable.version` from the official `version.json`.
2. Stop without work when an existing same-version Jenny92 release is complete.
3. Rebase the maintained commit stack onto the exact official stable tag.
4. Refuse publication if the reviewed official `tools/installer.sh` checksum changed.
5. Run MiniLoong, runtime-archive, BusyBox font and workflow tests.
6. Build and extract the final archive, repeat the packaged platform tests, then install
   the exact archive through Port App Manager's current Rust installer for both legacy
   MiniLoong and current LoongOS configurations.
7. Push the validated candidate and rebuild it in the publish job.
8. Create a draft release, verify its exact asset list, then publish it.

The workflow stores no intermediate Actions artifacts. `validate_only` is enabled by
default for manual runs; clear it only when the validated stable should be published.
Scheduled runs publish a missing stable automatically.

## Manual validation

Validate the current branch against an available official stable tag:

```bash
PORTMASTER_CONSUMER_ROOT=/path/to/portmaster-launcher-pack \
  tools/validate-maintained-candidate.sh 2026.06.23-0015 /tmp/maintained-release
```

The validator enforces the downstream file allowlist and the reviewed installer
baseline in `upstream-baseline.json`. When upstream changes its installer, review the
diff, synchronize only behavior that the App Manager protocol actually needs, update
the baseline, and rerun the complete validation. Never bypass the drift gate.

## Port App Manager contract

Port App Manager owns device and path discovery through its generated configuration.
Its in-process Rust installer stages the already downloaded archive, replaces only the
resolved managed entries, installs the configured frontend launcher and preserves live
runtime/configuration data. It performs no network access and no device guessing.

The consumer-side candidate test lives in `jenny92-tech/portmaster-launcher-pack` and
is checked out by CI. It installs the exact built `PortMaster.zip` under synthetic
legacy MiniLoong and current LoongOS roots, checks executable launchers, then performs
an update and verifies preserved directories. Any install-contract change must update
both repositories and pass this cross-repository candidate validation before release.
