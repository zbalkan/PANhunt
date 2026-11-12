# PANhunt scheduled profiles

This directory provides a template service and timer. Install
`panhunt@.service`, `panhunt@.timer`, and `panhunt-alert@.service`
under `/etc/systemd/system/`. Install the existing profile files under
`/etc/panhunt/` using the filename convention `panhunt-<profile>.ini`.

The example `panhunt-var-log.ini` scans `/var/log`. Its report and JSON
directories are `/var/log/panhunt/var-log`. For a second example,
`panhunt-opt.ini` scans `/opt` and uses `/var/log/panhunt/opt`.
Enable independent schedules with `systemctl enable --now panhunt@var-log.timer`
and `systemctl enable --now panhunt@opt.timer`.

Other **example** locations for log-pipeline auditing include an rsyslog
work directory (`/var/lib/rsyslog` or `/var/spool/rsyslog`, depending on
configuration), Fluentd / td-agent or Fluent Bit file-buffer directories,
and `/var/log/masked`. Define separate profiles for those locations using
the installed paths, not assumed defaults. For a log profile, exclude
`/var/log/panhunt` to avoid rescanning generated reports.

The `panhunt` service identity requires explicit filesystem permissions.
Grant narrowly scoped read-only ACLs or suitable read-only group membership
for protected log directories. `ReadOnlyPaths=` does not itself grant
filesystem access. The restricted service should not execute document
parsers as root. Confirm the host's `systemd-journal` group or ACL policy
before reading journald; direct journal files are **not** supported as
a reliable detection source. Use `journalctl -o export` instead of
`-o json` because binary fields may be encoded as numeric arrays.

With exit code 1 (findings) or 2 (incomplete/error), `OnFailure=` invokes
the metadata-only alert unit. Exit 130 is treated as interruption and does
not trigger the alert. Operational alert routing should forward the unit
event to the SIEM. The template's report path is instance-specific;
`%i` is the escaped instance identifier. Use a restricted set of
ASCII letters, digits, and hyphens for instance names. Verify that configured
report paths match each instance, and ensure only one scan per instance
writes its report directory at a time.

For shell-based journald pipelines use `set -o pipefail`, so a failed
`journalctl` process cannot appear as a successful scan. An empty input
stream does not prove journal coverage. Bound scans by time or cursor and
retain the range externally. For a pipeline executed inside a systemd unit,
use a separate explicitly configured pipeline service rather than
passing a shell pipeline as arguments to `ExecStart=`.

**Scope:** A clean outcome means no PAN matching the configured detection
policy was found in successfully inspected content in the configured
paths. This cannot establish absence in core dumps, swap, backups, remotely
forwarded SIEM data, encrypted objects, unsupported Fluent Bit buffer formats,
or encodings outside the scanner's supported policy. Incomplete, unreadable,
and excluded content must be recorded and investigated.
