# Security Policy

## Supported Versions

Only the latest release receives security fixes.

| Version | Supported |
|---------|-----------|
| latest  | Yes       |
| older   | No        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security bugs.**

Email: sigilvoid@gmail.com
Response time: 24 hours
Fix timeline: 3 days for critical, 2 weeks for moderate (Skipping weekdays and Government issued holidays)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Scope

Rex runs as a user-space daemon with microphone and filesystem access. The following are considered in-scope vulnerabilities:

- Audio capture triggered without user input
- Arbitrary code execution via malformed config
- API key or sensitive data exposed in logs or notifications
- Privilege escalation via the systemd service
- Insecure IPC — commands accepted from other users via the unix socket

## Out of Scope

- Issues in upstream dependencies (faster-whisper, Piper, etc.) — report those upstream
- Attacks requiring physical access to the machine
- Social engineering
