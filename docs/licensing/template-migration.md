# Local templates and upgrades

A fresh installation no longer includes CMR, CIM/CUV, IATA DGD, AVC or the
sixteen regulatory model PDFs. Administration → Document templates lists each
supported edition and its availability. Import an authorised original, record
its source and basis for local use, and preview it. An incompatible file does
not replace the current one. A new edition needs a mapping/compatibility review.

An in-app Docker update uses the helper from the new image. Before stopping the
old container it copies only the registered, compatible PDFs from that container
into the existing data volume, preserving the original local terms. It never
copies those files to a repository, release or remote service. A failed
preservation stops the update while the old container can still run.

The updated native installer likewise retains compatible files from the old
`current` release before changing the symlink, and removes the obsolete PyMuPDF
package from its dedicated runtime environment. Migration reads an existing
`DATA_DIR` from `/etc/emcargo/emcargo.env`, without executing or logging that file. Use the new installer for this
migration. The previous version's installer cannot execute logic it never had.

For manual container/Kubernetes replacements, preserve the existing authorised
PDFs in the persistent volume before replacing the old image. Existing forms in
`<DATA_DIR>/templates/forms/` and registered models in the regulations store are
recognised by their compatibility hashes. Imported versions live in
`<DATA_DIR>/document-templates/` and survive image replacement.

Saved shipment documents are not edited or deleted. A newly requested document
is subject to current source and template checks; a previously stored PDF
remains an historical record, not a new compliance determination.

Only pypdf performs form filling and model-page selection; ReportLab supplies
signatures/overlays. The isolated packing-list reader uses pypdf for text and
PDFium for raster previews/OCR. Production no longer imports PyMuPDF. Developer
extractors/tests still use PyMuPDF and retain their separate licensing review.
