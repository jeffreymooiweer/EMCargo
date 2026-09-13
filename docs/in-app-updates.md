# In-app updates

Administrators use **Settings → Updates** to see the running version, check
for a release, read the release notes and install it where the installation
supports this. The update notification opens this same page. The legacy
`/settings?tab=maintenance` link redirects to this section.

## Docker Compose

In-app updates are enabled by default for administrators. The application must
use the official image and have access to the Docker socket. Socket access
grants control of the Docker host; enable it only for a trusted installation.
The base Compose file keeps this optional.

From the existing project directory, enable the provided override:

```bash
docker compose -f docker-compose.yml -f docker-compose.updates.yml up -d
```

The override mounts
`/var/run/docker.sock:/var/run/docker.sock`. The standard image entrypoint
adds its application user to the socket's group; it does not change host
socket permissions. Installations overriding the image user or entrypoint
must provide the appropriate group access themselves.

The separate **Check for updates** switch controls release-feed requests.
If it is off, neither passive nor manual checks contact GitHub. Turning it
on does not itself authorize installation or grant Docker access.

## Unraid

The Unraid template includes **Docker socket (in-app updates)** in the normal
settings view, with `/var/run/docker.sock` as both the host and container path
and read/write access. Its description explains the purpose and permissions.
The socket connects EMCargo to Unraid's Docker engine so an administrator can
install an update and replace/restart the application container from the app.
This grants full Docker control and can provide administrator-level access to
the Unraid host; use it only with a trusted image. Updates still require an
administrator's confirmation in EMCargo. Removing the mapping leaves the
application usable, with updates managed through Unraid instead.

For an existing installation, edit the container in Unraid and add or fill in
this path once if it is absent or empty, then apply the template. Older templates
may list it as **Docker socket (optional)** under advanced settings. Updating the
repository template or pulling an image cannot add a mount to a running container.

The former `UPDATE_APPLY_ENABLED` variable is retired and ignored, including
an existing `false` value. No replacement switch is needed. Installations still
running an older release with in-app updates disabled need one update from
Unraid's Docker tab to receive this change.

Open **Settings → Updates**. The capability result explains a missing socket,
permission, container identity or official image separately. Once it
reports ready and a newer release is available, the installation button is
enabled. Confirming it starts the pull and restart.

## Progress and recovery

A short-lived helper from the new image replaces the application container.
Its progress is written atomically to `DATA_DIR/update-state.json`; the page
can resume observing it after navigation or a server restart. Bind mounts and
Docker `HostConfig.Mounts` are passed to the helper, including a custom data
path, without adding the socket twice. A configured Docker health check must
be healthy before the previous container is removed. Startup failure invokes
the existing container rollback; failure details remain on the Updates page.

The page compares the running version before resuming saved progress. Once the
target answers, the existing observer reloads the page once to load the new UI;
opening that version again does not resume an old restart message. A delayed
helper record therefore cannot cause a refresh loop. A completion record from
an earlier operation cannot trigger a reload before the current target answers.
Progress responses and the HTML entry point are not cached across updates, and
reading progress does not consume completion or erase a concurrent update.

Maintain ordinary data backups. A container rollback is not a database backup
or a general migration rollback. Complex network or container configurations
should continue to use their operator-managed update procedure. Native and
Kubernetes installations display their own update command instead of offering
an impossible Docker replacement.

This change does not install or publish a release by itself. The release must
first exist in GitHub and the corresponding official GHCR image must be
published. The 2.2.0 implementation was tested against a simulated Docker API;
a real Unraid/Docker daemon replacement was not performed in the development
workspace.

Docker request shapes follow the [Docker Engine API reference](https://docs.docker.com/reference/api/engine/version/v1.45/).
