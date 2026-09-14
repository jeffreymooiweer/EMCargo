# Installing without Docker

## Native service

Use the installer from this repository. It downloads the native bundle attached to
an EMCargo release and installs the backend, built frontend and document templates.
New bundles use `emcargo-<version>-native.tar.gz`. The service is `emcargo`,
installed under `/opt/emcargo`, with settings in `/etc/emcargo/emcargo.env` and
data in `/var/lib/emcargo`. Existing installations must follow
[identity migration](identity-migration.md) first.

Requirements: Linux with systemd, Python 3.12 with venv, curl, tar and root access.

```bash
curl -fsSL https://raw.githubusercontent.com/jeffreymooiweer/emcargo/main/deploy/native/install.sh -o install.sh
sudo bash install.sh --bundle /path/to/emcargo-VERSION-native.tar.gz
```

Set `ADMIN_PASSWORD`, `PUBLIC_URL` and `CORS_ALLOWED_ORIGINS` in the generated
environment file before exposing the service. The backend listens on
`127.0.0.1:8080`; terminate HTTPS at your reverse proxy.

For updates, run `deploy/native/update.sh` from the current installed release as
root, optionally passing the release version. Keep the migrated data directory and environment file. Back up the data directory before updating.
The in-app Docker updater does not apply to native installations.

See [the installer](../deploy/native/install.sh),
[the updater](../deploy/native/update.sh) and [configuration](configuration.md).

## Document OCR

For scanned packing lists and photos, install Tesseract on the service host.
On Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-nld tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-fra
tesseract --list-langs
```

The `emcargo` service user must be able to find `tesseract` on `PATH`. The native
installer does not install operating-system packages automatically. Docker images
already include these dependencies. Without Tesseract, text-only PDFs still work;
scans and photos show an explicit missing-OCR message. Missing preferred language
data falls back to installed English with a visible notice.

Document proposals require the existing locally installed assistant model. Reading
supports PDF/JPEG/PNG, at most 20 MB, 10 pages and 40,000 recognised characters.
Source files are deleted after reading; selected source excerpts are part of the
user's saved draft. No upload is sent to an external OCR or model provider.

## Kubernetes

The manifest for new installations is [emcargo.yaml](../deploy/kubernetes/emcargo.yaml).
Set the administrator password, ingress hostname, TLS and storage size first.

```bash
kubectl apply -f deploy/kubernetes/emcargo.yaml
kubectl -n emcargo set image deployment/emcargo emcargo=ghcr.io/jeffreymooiweer/emcargo:2.0.0
```

Use one replica and the `Recreate` strategy because the application uses SQLite.
For an existing cluster, update its current deployment and preserve its namespace
and persistent volume claim. Applying the renamed manifest alongside it creates
separate resources; it does not migrate the database.

## Persistent data

Keep the complete `DATA_DIR`, including the database, uploads, branding, UN cards
and secret key. The `ADMIN_*` variables bootstrap the first account only. Existing
accounts are managed in the application. Shipment history is configured under
**Settings → Administration → Keep shipments**.
