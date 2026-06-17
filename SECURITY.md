Security Policy for pearOS
At Pear Software and Services, we are committed to maintaining the integrity, confidentiality, and availability of your system. Because pearOS operates as a rolling release distribution, security is treated as a continuous, iterative process rather than a static milestone.

Reporting Vulnerabilities
If you discover a security vulnerability in pearOS or in any Pear Software and Services product, we encourage you to report it immediately. Please prioritize responsible disclosure to protect our user base.

How to report: Send an email to alex@pear-software.com

What to include:

A clear description of the vulnerability.

Steps to reproduce the issue.

Impact assessment (how it affects the system or user data).

Any suggested mitigations or patches.

We aim to acknowledge reports within 48 hours and will work diligently to verify and remediate confirmed issues.

Security Philosophy: Rolling Release Model
In a rolling release environment, "security" means keeping components at their latest stable versions to ensure patches are applied as soon as upstream maintainers release them.

Continuous Updates: We encourage all users to run full system upgrades regularly using our package manager. We recommend pear-update to ensure all core libraries and kernel components receive the latest security patches.

Upstream Reliance: We rely on the security audits and fixes provided by the upstream projects (Linux Kernel, GNU, etc.). We verify these packages in our staging repository before pushing them to the rolling release channel.

Transparency: Our repository build logs are publicly accessible, allowing the community to audit what goes into the packages.

Best Practices for Users
As a user of a rolling release distribution, you hold a critical role in your own security posture:

Keep it Current: Since this is a rolling release, running outdated software increases your attack surface.

Bash
# Ensure your system is always up to date
Verify Sources: Only install packages from our official repositories. Third-party repositories or manual binaries carry inherent risks.

Kernel Management: We provide the latest stable kernels. If you are experimenting with experimental/RC kernels, be aware that they may have a different security profile than our main production kernel.

Use sudo Responsibly: Never run commands with elevated privileges unless absolutely necessary.

Security Updates & Notifications
Given the nature of rolling releases, security advisories are often bundled directly into our update changelogs.

Critical Updates: For high-severity vulnerabilities (e.g., kernel-level exploits), we will issue a special announcement via our official website and the pearOS dashboard.

Automated Security: We are working on integrating automated security scanning tools that notify users if their installed package versions are flagged as vulnerable by common CVE databases.

Legal & Compliance
pearOS is an open-source project. While we take every precaution to secure the distribution, software is provided "as is." We assume no liability for data loss or system compromise resulting from the use of our software. We expect all contributors to adhere to ethical standards when contributing to the security of our codebase.

Last updated: June 2026
