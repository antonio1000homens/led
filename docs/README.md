# Documentation

Cross-cutting repository documentation lives here. Hardware-specific documentation
lives beside the hardware it describes.

## Repository

- [Deployment](DEPLOYMENT.md) — AWS, CloudFront, Cloudflare, SSM and production rollout.
- [Control plane](CONTROL_PLANE.md) — admin/control API architecture and security boundaries.
- [GitHub Actions ownership](WORKFLOWS.md) — path-scoped CI/CD responsibilities.

## Hardware documentation

- [MatrixPortal S3](../hardware/matrixportal/README.md)
  - [Performance and refresh architecture](../hardware/matrixportal/docs/matrixportal-performance.md)
  - [Hardware refresh experiment record](../hardware/matrixportal/docs/HARDWARE_REFRESH_EXPERIMENT.md)
  - [MQTT hardware validation](../hardware/matrixportal/docs/MQTT_HARDWARE_VALIDATION.md)
- [Enclosure](../hardware/enclosure/README.md)
  - Direct-mount design docs are under `hardware/enclosure/direct-mount/docs/`.
