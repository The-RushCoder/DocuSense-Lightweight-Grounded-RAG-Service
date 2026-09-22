# TechNova Corporation — Internal Policy Document

**Document ID:** TNP-2024-001  
**Version:** 3.2  
**Classification:** Internal — Confidential  
**Owner:** Information Security & Compliance Team  
**Last Reviewed:** October 2024  
**Next Review:** October 2025  

---

## Introduction

This document defines the official internal policies of **TechNova Corporation** ("the Company"), a fictional mid-sized software services firm headquartered in Meridian City. All employees, contractors, and third-party vendors with access to TechNova systems must read, understand, and comply with these policies.

Failure to comply may result in disciplinary action up to and including termination of employment or contract. Policy violations that involve regulatory breaches may also be reported to the relevant authorities.

Questions regarding this document should be directed to: **security@technova.example.com**

---

## 1. Information Security Policy

### 1.1 Purpose

TechNova Corporation is committed to protecting the confidentiality, integrity, and availability of all information assets. This policy establishes the baseline security requirements for all systems, personnel, and processes that handle Company data.

### 1.2 Scope

This policy applies to all:
- Full-time and part-time employees
- Contractors and consultants
- Third-party service providers with system access
- Interns and temporary staff

### 1.3 Information Classification

All Company data must be classified into one of four tiers:

| Tier | Label | Description |
|------|-------|-------------|
| 1 | Public | Marketing materials, press releases |
| 2 | Internal | General business communications |
| 3 | Confidential | Customer data, financial records |
| 4 | Restricted | Encryption keys, credentials, PII |

Tier 3 and Tier 4 data must be encrypted at rest using AES-256 and in transit using TLS 1.2 or higher.

### 1.4 Responsibilities

- **Chief Information Security Officer (CISO):** Owns this policy and is responsible for annual review.
- **IT Department:** Implements and enforces technical controls.
- **All Employees:** Responsible for adhering to the policy and reporting violations immediately.

---

## 2. Database Backup Policy

### 2.1 Purpose

To ensure that all primary and secondary databases can be restored to a known-good state in the event of data loss, corruption, or system failure.

### 2.2 Backup Schedule

All production databases must be backed up according to the following schedule:

| Backup Type | Frequency | Method |
|-------------|-----------|--------|
| Full Backup | Weekly (Sunday 02:00 UTC) | Snapshot |
| Differential Backup | Daily (02:00 UTC) | Incremental |
| Transaction Log | Every 4 hours | Log shipping |

### 2.3 Backup Retention

All primary database backups are retained for a rolling period of **30 calendar days**. After 30 days, backups are automatically purged from the primary backup storage.

Long-term archival backups are taken on the **first Sunday of each quarter** and retained for **12 months** in cold storage (TechNova Glacier Archive).

Transaction logs are retained for **7 days** to support point-in-time recovery within that window.

### 2.4 Backup Verification

Each backup must be verified through an automated integrity check within **4 hours of completion**. The backup verification system will:
1. Restore a sample of the backup to an isolated test environment.
2. Run a suite of consistency checks.
3. Generate a verification report.

Any backup that fails verification must be flagged immediately to the DBA on-call team via PagerDuty alert code **DB-BACKUP-FAIL**.

### 2.5 Backup Storage Locations

- **Primary:** TechNova Internal Storage Array (on-premises)
- **Secondary:** TechNova Cloud Backup (TechNova Private Cloud Region: MRD-1)
- **Archival:** TechNova Glacier Archive (offsite, encrypted)

Backups must never be stored on the same physical host as the source database.

---

## 3. Password Policy

### 3.1 Password Requirements

All employee and system account passwords must meet the following minimum requirements:

- Minimum length: **14 characters**
- Must contain at least: 1 uppercase letter, 1 lowercase letter, 1 digit, 1 special character
- Must not contain the user's full name, username, or email address
- Must not be one of the user's previous **12 passwords**
- Must not be a commonly known password (checked against the HIBP database)

### 3.2 Password Expiration

Standard user passwords must be changed every **90 days**.  
Privileged account passwords (admin, root, service accounts) must be changed every **30 days**.

### 3.3 Multi-Factor Authentication (MFA)

MFA is **mandatory** for:
- All VPN connections
- All cloud management consoles
- All administrative interfaces
- All remote desktop sessions
- GitHub and CI/CD platforms

Acceptable MFA methods:
- TOTP authenticator app (Google Authenticator, Authy)
- Hardware security key (YubiKey 5 series or equivalent)

SMS-based OTP is **not permitted** for privileged access.

### 3.4 Password Storage

Passwords must never be stored in plain text. All systems must use:
- **bcrypt** (cost factor ≥ 12) or
- **Argon2id** for new implementations

Passwords must never be logged, transmitted in query strings, or stored in version control.

---

## 4. Access Control Policy

### 4.1 Principle of Least Privilege

All user and service accounts must be granted the minimum level of access required to perform their job functions. Access rights must be reviewed every **6 months** by the account owner's manager.

### 4.2 Access Provisioning

New access requests must be submitted through the **TechNova IAM Portal** (iam.technova.example.com). Each request requires:
- Business justification
- Manager approval
- IT Security review for Tier 3/4 data access

Provisioning must be completed within **2 business days** of full approval.

### 4.3 Access Revocation

Access must be revoked within **4 hours** of:
- Employee termination or resignation
- Contractor engagement end
- Role change that no longer requires the access

Automated de-provisioning workflows are triggered by the HR system upon employment status change.

### 4.4 Privileged Access Management

Privileged accounts (domain admin, database admin, root) must:
- Be registered in the TechNova PAM vault (CyberArk)
- Use session recording for all privileged sessions
- Not be used for day-to-day non-administrative tasks
- Require dual approval for production database access

---

## 5. Incident Reporting Policy

### 5.1 What to Report

Employees must immediately report any of the following:
- Suspected unauthorized access to systems or data
- Phishing emails received or clicked
- Lost or stolen devices containing Company data
- Malware detection
- Unusual system behavior
- Policy violations observed in colleagues

### 5.2 How to Report

Security incidents must be reported via one of the following channels:

- **Email:** security-incidents@technova.example.com
- **Hotline:** +1-800-555-0199 (available 24/7)
- **Internal Portal:** https://incidents.technova.example.com

Employees must report incidents within **1 hour** of discovery. Waiting to investigate before reporting is not permitted.

### 5.3 Incident Response SLAs

| Severity | Definition | Initial Response | Resolution Target |
|----------|------------|-----------------|-------------------|
| P1 — Critical | Data breach, ransomware | 15 minutes | 4 hours |
| P2 — High | Unauthorized access | 30 minutes | 8 hours |
| P3 — Medium | Policy violation | 2 hours | 24 hours |
| P4 — Low | Suspected phishing | 4 hours | 72 hours |

### 5.4 Non-Retaliation

TechNova maintains a strict non-retaliation policy. Employees who report security incidents in good faith will not face disciplinary action, even if the report proves unfounded.

---

## 6. Data Retention Policy

### 6.1 Retention Schedule

All Company data must be retained according to the following schedule:

| Data Type | Retention Period | Disposal Method |
|-----------|-----------------|-----------------|
| Customer contracts | 7 years | Secure deletion |
| Financial records | 7 years | Secure deletion |
| Employee records | Duration + 5 years | Secure deletion |
| System logs | 12 months | Automated purge |
| Security audit logs | 24 months | Secure deletion |
| Email communications | 3 years | Archive then delete |
| Database backups | 30 days (primary), 12 months (archive) | Automated purge |

### 6.2 Data Disposal

When data reaches its end-of-life retention period:
- Electronic data must be overwritten using **DoD 5220.22-M** standard (7-pass wipe) or cryptographic erasure.
- Physical media must be destroyed using a certified destruction service. Certificates of destruction must be retained for 2 years.

### 6.3 Legal Hold

If legal proceedings are anticipated, the Legal Department may impose a **legal hold**, which suspends all automated deletion for specified data sets. Legal holds supersede standard retention schedules.

---

## 7. API Security Policy

### 7.1 Authentication

All internal and external APIs must implement authentication using one of:
- **OAuth 2.0** with JWT bearer tokens (preferred)
- **API keys** with HMAC-SHA256 request signing

API keys must be rotated every **90 days**. Compromised keys must be revoked within **15 minutes** of discovery.

### 7.2 Authorization

APIs must implement role-based access control (RBAC). Each endpoint must explicitly define the minimum required role. No endpoint may be publicly accessible without explicit Security Team approval.

### 7.3 Rate Limiting

All public-facing APIs must implement rate limiting:
- **Standard tier:** 100 requests per minute per API key
- **Premium tier:** 1,000 requests per minute per API key
- **Internal services:** No rate limit, but monitored for anomalies

### 7.4 Input Validation

All API inputs must be validated and sanitized server-side. APIs must:
- Reject payloads exceeding **10 MB**
- Validate all query parameters against an allowlist
- Return generic error messages (no stack traces in production)
- Log all 4xx and 5xx responses

### 7.5 Transport Security

All API traffic must use **TLS 1.2 or higher**. TLS 1.0 and 1.1 are prohibited. Self-signed certificates are not permitted in production environments.

---

## 8. Software Deployment Policy

### 8.1 Deployment Pipeline

All software deployments to production environments must pass through the following pipeline stages:

1. **Development** — Local development and unit testing
2. **Staging** — Integration testing and QA validation
3. **Pre-production** — Load testing and security scanning
4. **Production** — Approved deployment with rollback plan

Skipping stages requires CISO and CTO dual approval, documented in the change management system.

### 8.2 Deployment Approvals

| Environment | Required Approvals |
|-------------|-------------------|
| Development | None (self-service) |
| Staging | Team lead |
| Pre-production | Engineering manager |
| Production | Engineering manager + Security review |

Production deployments are only permitted during the **maintenance window: Tuesdays and Thursdays, 22:00–02:00 UTC**, unless a P1 emergency patch is required.

### 8.3 Rollback Requirements

All production deployments must include a documented rollback plan. Rollback must be executable within **15 minutes** of a deployment failure. Deployment engineers must rehearse rollback procedures in pre-production at least once per quarter.

---

## 9. Change Management Policy

### 9.1 Change Categories

| Category | Description | Lead Time |
|----------|-------------|-----------|
| Standard | Pre-approved, low-risk changes | 3 business days |
| Normal | Moderate-risk changes | 5 business days |
| Emergency | Critical fixes for P1 incidents | As needed |

### 9.2 Change Approval Board (CAB)

Normal and Emergency changes must be reviewed by the Change Approval Board, which meets every **Wednesday at 14:00 UTC**. Emergency changes may be approved asynchronously via the on-call CAB member.

### 9.3 Change Freeze Periods

No changes to production systems are permitted during:
- Last 2 weeks of each fiscal quarter
- Company-designated holidays
- Major product release windows (communicated via the Engineering Calendar)

Exceptions require dual approval from CTO and CISO.

---

## 10. Employee Device Security Policy

### 10.1 Managed Devices

All employees handling Tier 3 or Tier 4 data must use Company-managed devices. Managed devices must have:
- **Full disk encryption** (BitLocker for Windows, FileVault for macOS)
- **Endpoint Detection and Response (EDR)** agent (CrowdStrike Falcon)
- **Mobile Device Management (MDM)** enrollment (Jamf for macOS, Microsoft Intune for Windows)
- Screen lock activating after **5 minutes** of inactivity
- Automatic OS and security patch installation within **72 hours** of release

### 10.2 Personal Device (BYOD)

Personal devices may only access Company systems through:
- The TechNova VPN with MFA
- Company-approved containerized mobile apps

Personal devices must not store Tier 3 or Tier 4 data locally.

### 10.3 Lost or Stolen Devices

Lost or stolen Company devices must be reported to the IT Security team within **30 minutes** of discovery. The IT team will initiate a remote wipe within **1 hour** of the report. Employees must not attempt to recover data from wiped devices.

---

## 11. Remote Access Policy

### 11.1 VPN Requirements

Remote access to TechNova internal systems is only permitted through the **TechNova Enterprise VPN** (Palo Alto GlobalProtect). All VPN connections require:
- Valid employee credentials
- MFA (TOTP or hardware key)
- Company-managed device (for production access)

### 11.2 Split Tunneling

Split tunneling is **disabled** on all VPN profiles for employees with access to Tier 3/4 data. All traffic must route through TechNova network inspection when connected to VPN.

### 11.3 Session Limits

VPN sessions automatically terminate after **8 hours** of inactivity. Users must re-authenticate to resume. Concurrent VPN sessions from different geographic locations trigger an automatic security alert.

---

## 12. Logging and Monitoring Policy

### 12.1 Mandatory Log Sources

The following systems must generate security-relevant logs:
- Authentication systems (login success, failure, lockout)
- Privileged access sessions
- Database query logs (for Tier 3/4 databases)
- API gateway access logs
- Firewall and network flow logs
- Endpoint EDR events

### 12.2 Log Retention

Security logs must be retained for a minimum of **12 months** in hot storage and **24 months** in archive storage. Logs must be stored in a tamper-evident format and replicated to an independent logging platform (Splunk SIEM).

### 12.3 Alerting SLAs

| Alert Type | Response Time |
|------------|--------------|
| Failed login > 5 in 10 minutes | 5 minutes |
| Privileged account anomaly | 10 minutes |
| Data exfiltration indicator | 5 minutes |
| Malware detection | Immediate (auto-isolate) |

---

## 13. Disaster Recovery Policy

### 13.1 Recovery Objectives

TechNova's disaster recovery targets are:

| System Tier | RTO | RPO |
|-------------|-----|-----|
| Tier 1 — Mission Critical | 1 hour | 15 minutes |
| Tier 2 — Business Critical | 4 hours | 1 hour |
| Tier 3 — Standard | 24 hours | 4 hours |
| Tier 4 — Non-critical | 72 hours | 24 hours |

**RTO** = Recovery Time Objective (maximum acceptable downtime)  
**RPO** = Recovery Point Objective (maximum acceptable data loss window)

### 13.2 DR Testing

Disaster recovery procedures must be tested at minimum:
- **Full DR drill:** Once per year (typically in Q3)
- **Partial restore test:** Quarterly
- **Backup restore test:** Monthly

Test results must be documented and reviewed by the CISO within **5 business days** of the test.

### 13.3 DR Site

TechNova maintains a warm standby DR site in the **Westfield Data Center** (WDC-2), located 200 kilometers from the primary data center. Failover to WDC-2 is automated for Tier 1 systems and manual for Tier 2–4.

---

## 14. Business Continuity Policy

### 14.1 Business Continuity Plan (BCP)

TechNova maintains a Business Continuity Plan covering scenarios including:
- Natural disaster (flood, fire, earthquake)
- Extended power outage (> 4 hours)
- Cyber attack (ransomware, DDoS)
- Key personnel unavailability
- Critical vendor failure

### 14.2 BCP Review and Maintenance

The BCP is reviewed and updated:
- Annually (full review by Business Continuity Committee)
- After any P1 incident that invoked continuity procedures
- After significant organizational changes

### 14.3 Communication During Disruption

During a declared business continuity event, the designated **Incident Commander** is responsible for all internal and external communications. Employees must follow instructions from the Incident Commander and must not communicate with media or external parties without authorization from the Corporate Communications team.

### 14.4 Critical Supplier Management

A list of critical suppliers is maintained in the Supplier Risk Register. For each critical supplier, a contingency plan must exist describing:
- Alternative suppliers
- Maximum tolerable disruption period
- Escalation contacts

The Supplier Risk Register is reviewed every **6 months** by the Procurement and Security teams.

---

## 15. Policy Compliance and Enforcement

### 15.1 Compliance Monitoring

The Information Security team performs:
- Quarterly automated compliance scans
- Annual third-party security audits
- Continuous vulnerability scanning of internet-facing systems

### 15.2 Violations

Policy violations are handled as follows:

| Violation Type | Action |
|---------------|--------|
| Minor (first offense) | Mandatory retraining |
| Minor (repeat offense) | Written warning |
| Major violation | Formal disciplinary action |
| Gross misconduct | Immediate termination |

### 15.3 Policy Exceptions

Exceptions to this policy must be submitted to the CISO via **security@technova.example.com** with:
- Description of the exception required
- Business justification
- Risk assessment
- Compensating controls

All exceptions must be re-evaluated annually.

---

*This document is the property of TechNova Corporation. All information herein is fictional and for demonstration purposes only. Any resemblance to real companies, policies, or individuals is coincidental.*

*End of Document — TNP-2024-001 v3.2*
