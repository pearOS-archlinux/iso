# Contributing to pearOS

Thank you for your interest in contributing to **pearOS**! As a rolling release distribution, our project thrives on the collaboration of developers, testers, and power users who want to keep the system modern, stable, and secure.

## Getting Started

Whether you are here to fix a bug, suggest a feature, or improve documentation, your help is appreciated. 

1. **Fork the repository:** Work on your own copy of the codebase.
2. **Environment:** Ensure you have the necessary build tools installed for our packaging format.
3. **Branching:** Please use a descriptive branch name (e.g., `fix/wifi-driver-issue` or `feat/ui-refinement`).

## Development Workflow

Because pearOS is a **rolling release**, we prioritize stability alongside cutting-edge updates.

### 1. Reporting Issues
Before opening a new issue, please check the existing issue tracker to avoid duplicates. When reporting:
* Use the provided **Issue Template**.
* Include the version of the kernel and core components you are currently running (`uname -a`, `pear-version`).
* Attach logs (e.g., `journalctl -b`) if the issue involves a crash or driver failure.

### 2. Pull Requests (PRs)
* **One change per PR:** Keep your contributions focused.
* **Testing:** If you are updating a package or adding a feature, demonstrate that you have tested it in a clean environment.
* **Upstream First:** If you are fixing a bug in an upstream application, we highly encourage you to submit the patch to the original project first, then notify us so we can include it in our next update.
* **Documentation:** If your change adds a new feature or changes command-line behavior, please update the corresponding documentation.

## Coding Standards

* **Readability:** Keep code clean and follow the existing style conventions of the specific component you are modifying.
* **Commit Messages:** Follow conventional commit standards:
    * `feat:` (new feature)
    * `fix:` (bug fix)
    * `docs:` (documentation changes)
    * `style:` (formatting, missing semi-colons, etc.)
    * `refactor:` (code change that neither fixes a bug nor adds a feature)

## Community & Communication

pearOS is a community-driven project. We coordinate our efforts through:
* **Discord/Matrix:** [Insert Link]
* **Mailing List/Forum:** [Insert Link]

Please adhere to our [Code of Conduct] (if applicable).

## Legal & Licensing

By submitting a contribution to pearOS, you agree that your work will be licensed under the same terms as the pearOS project (typically GPL or compatible open-source licenses). Ensure that you have the right to submit the code you are providing.

## Rolling Release Maintenance

Since we aim for a "continuous update" model, please understand that:
* **Rapid Integration:** Your code may be merged and pushed to the `stable` branch quickly. Ensure it is production-ready.
* **Review Process:** We may request changes to ensure your code aligns with our current security and performance benchmarks.

*Last updated: June 2026*
