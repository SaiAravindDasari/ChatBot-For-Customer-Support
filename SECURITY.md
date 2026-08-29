# QueryDesk — Enterprise Security Policy & Hardening

## 1. Security Architecture

QueryDesk is designed according to Defense-in-Depth principles:

| Layer | Defense Mechanism | Implementation |
|---|---|---|
| **Network & Transport** | SSL/TLS, Secure Cookies, HSTS | Nginx / `SecurityHeadersMiddleware` |
| **Edge & Proxy** | DoS Protection & Rate Limiting | `limit_req_zone` (30 req/sec burst 50) |
| **Application Layer** | JWT RBAC & PBKDF2 Password Hashing | `backend/auth.py` (HMAC-SHA256, 200,000 iterations) |
| **Input Validation** | HTML Sanitization & Control Character Filtering | `backend/security.py` (`sanitize_input`) |
| **Database** | SQL Parameterization & WAL Concurrency | `aiosqlite` parameterized queries (zero SQLi risk) |
| **Observability** | Distributed Correlation IDs & Audit Logs | `TracingAndMetricsMiddleware` |

---

## 2. HTTP Security Headers

Every response is equipped with strict security headers:
- `Content-Security-Policy`: Restricts resource loading to authorized CDNs and self.
- `X-Frame-Options: SAMEORIGIN`: Defends against Clickjacking attacks.
- `X-Content-Type-Options: nosniff`: Prevents MIME-confusion attacks.
- `Referrer-Policy: strict-origin-when-cross-origin`: Minimizes leakage of sensitive URLs.
- `Permissions-Policy`: Restricts browser hardware access (e.g. camera, geolocation).

---

## 3. Role-Based Access Control (RBAC)

The platform separates user permissions into distinct scopes:
- **`user`**: Public unauthenticated access to customer chat and knowledge base searches.
- **`agent`**: Access to Live Agent Inbox, ticket takeover, customer messaging, and canned responses.
- **`admin`**: Full access to analytics summaries, quality reviews, training opportunities, and system configuration.

---

## 4. Reporting Vulnerabilities

To report a security vulnerability, please email `security@querydesk.io` with a detailed description and steps to reproduce.
