#!/usr/bin/env python3
from pathlib import Path


root = Path(__file__).resolve().parents[1]
workflow = (root / ".github/workflows/follow-official-stable.yaml").read_text(encoding="utf-8")
manual_workflow = (root / ".github/workflows/build-miniloong.yaml").read_text(encoding="utf-8")
validator = (root / "tools/validate-maintained-candidate.sh").read_text(encoding="utf-8")
builder = (root / "tools/build-maintained-release.sh").read_text(encoding="utf-8")
sources = (root / "release/portmaster-sources.sh").read_text(encoding="utf-8")
pugwash = (root / "PortMaster/pugwash").read_text(encoding="utf-8")

required = [
    'cron: "19 3 * * 0"',
    "workflow_dispatch:",
    "workflow_call:",
    "validate_only:",
    "description: Validate only; do not push or publish",
    "default: true",
    "name: Plan · official stable",
    "name: Validate · ${{ needs.plan.outputs.stable }}",
    "name: Publish · ${{ needs.plan.outputs.stable }}",
    "name: Summary · ${{ needs.plan.outputs.stable || 'unresolved' }}",
    "uses: actions/checkout@v5",
    "data['stable']['version']",
    'refs/tags/$STABLE:refs/upstream/stable/$STABLE',
    'refs/tags/$previous:refs/upstream/stable/$previous',
    "expected = {'PortMaster.zip', 'version.json', 'SHA256SUMS'}",
    'git rebase --onto "refs/upstream/stable/$STABLE" "refs/upstream/stable/$previous" miniloong-support',
    'PORTMASTER_OFFICIAL_STABLE_REF="refs/upstream/stable/$STABLE"',
    "repository: jenny92-tech/portmaster-launcher-pack",
    'PORTMASTER_CONSUMER_ROOT="$GITHUB_WORKSPACE/_consumer/portmaster-launcher-pack"',
    "data['stable_tag'] = sys.argv[1]",
    "git commit --amend --no-edit",
    "no maintained commits remain after rebase",
    'echo "Rebased $maintained_commits maintained commits."',
    "tools/validate-maintained-candidate.sh",
    "Stored Actions artifacts | None",
    "Intermediate artifact storage | **0 bytes**",
    "decision=resume",
    "resume validated draft release",
    "targetCommitish",
    'gh release upload "$STABLE"',
    "--clobber",
    "release asset digest mismatch",
    "--draft",
    'gh release edit "$STABLE"',
    "--draft=false",
]
for needle in required:
    assert needle in workflow, needle

assert workflow.count("source release/portmaster-sources.sh") == 3
assert '"$PORTMASTER_UPSTREAM_VERSION_URL"' in workflow
assert workflow.count('git remote add upstream "$PORTMASTER_UPSTREAM_GIT_URL"') == 2
assert "https://github.com/PortsMaster/PortMaster-GUI/releases" not in workflow
assert "https://github.com/PortsMaster/PortMaster-GUI.git" not in workflow
assert "actions/checkout@v4" not in workflow
assert "dry_run" not in workflow
assert "inputs.publish" not in workflow
assert "actions/upload-artifact" not in workflow
assert "actions/download-artifact" not in workflow
assert "prerelease" not in workflow.lower().replace("isprerelease", "")
assert workflow.count('git fetch --force upstream "refs/tags/$STABLE:refs/upstream/stable/$STABLE"') == 2
assert workflow.count('PORTMASTER_OFFICIAL_STABLE_REF="refs/upstream/stable/$STABLE"') == 2
assert workflow.count("repository: jenny92-tech/portmaster-launcher-pack") == 2
assert workflow.count('PORTMASTER_CONSUMER_ROOT="$GITHUB_WORKSPACE/_consumer/portmaster-launcher-pack"') == 2
assert workflow.index("tools/validate-maintained-candidate.sh") < workflow.index("git push --force-with-lease")
assert workflow.rindex("tools/validate-maintained-candidate.sh") < workflow.index("gh release create")
assert workflow.index("--draft") < workflow.index("--draft=false")
assert "tests/test_follow_stable_workflow.py" in validator
assert "PORTMASTER_OFFICIAL_STABLE_REF" in validator
assert "PORTMASTER_CONSUMER_ROOT" in validator
assert "PAM_PORTMASTER_CANDIDATE" in validator
assert "appmanager-installer.sh" not in validator
assert 'source "$ROOT/release/portmaster-sources.sh"' in validator
assert 'rm -rf "$OUTPUT"' not in builder
assert "PORTMASTER_RELEASE_CHANNEL = 'stable'" in builder
assert "PORTMASTER_RELEASE_URL = '{release_url}'" in builder
assert 'release_url = f"{fork_releases_url}/latest/download/"' in builder
assert "PORTMASTER_RELEASE_VALUES = ('stable', 'beta', 'alpha')" in builder
assert 'for channel in ("alpha", "beta", "stable")' in builder
assert '"md5": digest.hexdigest()' in builder
assert "PORTMASTER_RELEASE_CHANNEL = '$EXPECTED_RELEASE_CHANNEL'" in validator
assert "PORTMASTER_UPSTREAM_VERSION_URL" in sources
assert "PORTMASTER_UPSTREAM_GIT_URL" in sources
assert "JENNY92_PORTMASTER_GUI_RELEASES_URL" in sources
assert "JENNY92_PORTMASTER_GUI_RELEASE_ASSET_BASE" in sources
assert 'PORTMASTER_MAINTAINER = "Jenny92"' in pugwash
assert 'maintainer_label = f"Maintainer: {PORTMASTER_MAINTAINER}"' in pugwash
assert 'system_status["text"].splitlines()' in pugwash

manual_required = [
    "name: Build MiniLoong Package",
    "workflow_dispatch:",
    "type: choice",
    "default: validate",
    "- validate",
    "- publish",
    "uses: ./.github/workflows/follow-official-stable.yaml",
    "validate_only: ${{ inputs.mode != 'publish' }}",
    "contents: write",
]
for needle in manual_required:
    assert needle in manual_workflow, needle

assert "schedule:" not in manual_workflow
assert "gh release" not in manual_workflow

print("stable follower workflow tests: PASS")
