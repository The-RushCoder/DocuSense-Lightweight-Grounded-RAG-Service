# Internal Technology Policy

**Document ID:** POL-001
**Version:** 1.0
**Effective Date:** January 1, 2026

## 1. Purpose

This policy defines basic requirements for data security, database backup, system access, incident management, and production operations.

All employees and technical personnel must follow this policy.

## 2. Database Backup

Production databases must be backed up regularly.

* Incremental backups: Every 6 hours
* Daily full backup: Every 24 hours
* Backup retention: 30 days
* Critical database restoration tests: Every 90 days
* At least one backup copy must be stored separately from the primary database infrastructure.

## 3. Data Security

Company information is classified as Public, Internal, Confidential, or Restricted.

Employee passwords must:

* Contain at least 12 characters
* Include uppercase and lowercase letters
* Include numbers and special characters

Multi-factor authentication is required for administrative accounts.

API keys, passwords, and authentication tokens must never be stored in source code repositories.

## 4. User Access

Employees must receive only the permissions required for their responsibilities.

Access to critical systems must be reviewed every 90 days.

When an employee leaves the company, system access must be disabled within 4 hours of official notification.

Temporary elevated access should normally expire within 24 hours.

## 5. Incident Management

Security incidents and major system failures must be reported to the Security or Operations Team immediately.

Incident severity levels are:

* **Severity 1:** Critical production or sensitive-data impact
* **Severity 2:** High operational impact
* **Severity 3:** Moderate operational impact
* **Severity 4:** Low operational impact

Severity 1 incidents must be acknowledged within 30 minutes.

Severity 2 incidents must be acknowledged within 2 hours.

## 6. Software Development

All production code must be reviewed by at least one other developer before merging.

New features must include appropriate tests.

Production code must use an approved version-control system.

Production secrets and private keys must never be committed to repositories.

## 7. Production Deployment

Before a production deployment, the responsible engineer must verify:

* Required tests have passed
* Database migrations have been reviewed
* Configuration changes have been checked
* Rollback procedures are available

High-risk deployments should be performed during an approved maintenance window.

## 8. Business Continuity

Critical systems must have documented recovery procedures.

* Critical database RPO: 6 hours
* Critical application RTO: 4 hours
* Recovery exercises: At least once per year
* Business continuity review: Every 12 months

## 9. Third-Party Services

Third-party services that process company or customer data must be reviewed before production use.

Confidential or Restricted company information must not be uploaded to unapproved external AI tools or services.

## 10. Policy Review

This policy must be reviewed at least once every 12 months.

The Technology and Operations Department is responsible for maintaining the current approved version.
