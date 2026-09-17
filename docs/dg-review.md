# Roles and dangerous goods release

Since 2.4.0 EMCargo has four account roles. The administrator assigns privileged
roles under **Users**. An application role does not certify professional training
or appoint a statutory safety adviser; the organisation selects qualified people.

| Capability | User | Super User | DG Specialist | Admin |
|---|---|---|---|---|
| Create shipments, personal settings and own avatar | Yes | Yes | Yes | Yes |
| View kept shipments and trips | Own department | All departments | All departments | All departments |
| Manage ordinary users and Super Users | No | Yes | No | Yes |
| Assign or manage DG Specialist / Admin accounts | No | No | No | Yes |
| Manage departments and equipment | No | Yes | No | Yes |
| Set organisation details, default language and theme | No | Yes | No | Yes |
| Mail server, branding, connections, security policy, updates and AI configuration | No | No | No | Yes |
| View the DG review queue | Own submissions | Own submissions | All submissions | All submissions |
| Release DG shipments or request changes | No | No | Yes | No |
| Create and view DGSA reports | No | Only with admin opt-in | Yes | Yes |
| Change DG release policy or Super User report access | No | No | No | Yes |

Super Users cannot create, promote, change, disable, delete or reset the password
or second factor of either privileged role. The API enforces this as well as the
interface. Administrators retain account recovery and role assignment. Every
account continues to follow the installation's second-factor policy.

## Submission and release

**Settings → DG review and reporting → Require DG release** is **on by default**.
Once the wizard's selected documents and DG declaration are complete, choose
**Submit for review** in the final step. This deliberately stores the submitted
version, including document inputs, goods, declarations and any signature, in the
review queue. Ordinary non-DG shipments do not need this step.

The DG Specialist opens **DG review**, checks the read-only submitted data and
all document fields, and either releases it or requests changes with an explanation.
The submitter can see the result, reopen the version in the wizard, correct it and
submit another review. Pending status refreshes periodically in the final step.
The specialist role also handles its own submissions; this is a role-based
approval workflow, not an enforced separation between two different individuals.

Release applies to the exact submitted shipment and document inputs. It does not
make EMCargo a certification service or replace required declarations, signatures
or inspection of the actual load. Changes to values, quantities, documents,
language, profiles or signature require another review. Download, ZIP, mail,
completed-history saving and historical document/JSON downloads enforce this on
the server. Editing a browser status or reusing an approval id with changed
content does not release a new version. Draft saving and authenticated reference
cards remain usable before approval; card access still requires sign-in and the
administrator's card-link setting. Updates to software, sources or templates still
require checking the actual files before operational use.

Reopening and downloading the same released review reuses its kept shipment when
history is enabled, avoiding duplicate annual-report counts. Pending/rejected
reviews are not counted as completed shipments. Existing DG history records
without a matching release must be reopened and submitted before new operational
exports when the policy is enabled.

## Settings and storage

The administrator can switch the release requirement off. Existing reviews remain
visible and are not erased by the switch. DGSA access for Super Users is a separate
switch, **off by default**. Reports also require the optional shipment history;
review submissions alone do not create an annual activity history.

The `dg_reviews` table is created automatically at startup on an existing
installation. Existing users keep their roles. No regulatory datasets or previous
shipment records are rewritten by this upgrade. Assign at least one qualified DG
Specialist before colleagues need to release DG shipments.

Review storage is independent of optional shipment history. The submitter or admin
can remove a review after confirmation, which also revokes the associated release.
Disabling history or clearing kept shipments does not delete review submissions.
Review records have no automatic expiry; the operator defines and applies an
appropriate retention policy. They are part of normal database backups.

Public UN-card QR pages and PDFs continue to work without login when the
administrator enables card links. Review data is never exposed by those links.
