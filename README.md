# oasis-home-assignment
Oasis Home Assignment - NHI Ticket System

## Project Overview
IdentityHub is a Non-Human Identity (NHI) management platform designed to help organizations track and manage service accounts, API keys, service principals, and other machine identities across cloud environments.

This project is a proof-of-concept integration that allows users to report NHI findings (e.g., stale service accounts, overprivileged keys, expiring credentials) directly to their Jira workspace, ensuring security issues are tracked and remediated efficiently.

---

## Technical Requirements & Features

### 1. Authentication & Multi-Tenancy
* **Secure Login**: User authentication with secure session management and logout functionality.
* **Data Isolation**: Proper handling of multi-tenancy to ensure users only access their own data and integrations.
* **Jira Connectivity**: Ability to connect to an Atlassian Jira workspace after logging into the application.

### 2. NHI Finding Management (UI)
* **Project Selection**: Users can select or specify a Jira project from their connected workspace.
* **Issue Creation**: A dedicated form to create NHI findings with:
    * **Title (Summary)**: e.g., "Stale Service Account: svc-deploy-prod".
    * **Description**: Detailed context regarding the identity finding.

### 3. Recent Tickets View
* Displays a list of the **10 most recent tickets** created via this application for the selected project.
* Shows the ticket title and creation timestamp.
* Each ticket is clickable, opening the corresponding Jira issue in a new browser tab.

### 4. REST API for External Systems
* **Programmatic Integration**: A RESTful endpoint allowing external systems (scanners, CI/CD pipelines) to create tickets.
* **Security**: Requires an API key for authentication.
* **Robustness**: Includes input data validation and returns appropriate HTTP status codes and error messages.

---

## Bonus Feature: NHI Blog Digest
An automated background process (Trigger/Scheduled) that:
1.  Fetches the most recent blog post from `oasis.security/blog`.
2.  Generates an AI-powered summary of the post.
3.  Automatically creates a Jira ticket containing the blog title and summary.
*Note: This feature operates independently of the UI.*

---

## Architecture & Design Decisions
* **Separation of Concerns**: Clear distinction between the UI and backend layers for maintainability and scalability.
* **Security First**: Credential management follows secure coding standards to protect sensitive Jira API tokens.
* **UX/DX**: Error messages are designed to be meaningful to the end-user, and the API is designed for developer ease-of-use.