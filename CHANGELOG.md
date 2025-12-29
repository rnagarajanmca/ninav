# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-29

### Added
- Initial release of Ninav
- Photo gallery with grid and timeline views
- Automatic face detection using dlib
- Face clustering with similarity matching
- Person management (create, rename, assign faces)
- Docker Compose deployment
- SQLite database for metadata
- Responsive React frontend with TypeScript
- FastAPI backend with Python 3.12
- GPU acceleration support via optional GPU worker
- Real-time face scanning with progress tracking
- Image operations (rename, delete, favorite)
- Folder navigation and filtering
- Lightbox image viewer
- RESTful API with OpenAPI documentation

### GPU Worker
- Standalone GPU acceleration service
- InsightFace integration for 30-100x speedup
- CUDA support for NVIDIA GPUs
- Automatic fallback to CPU when unavailable
- 512-dimensional embeddings vs 128-dimensional
- Windows and Linux support

### Documentation
- Comprehensive README with quick start
- GPU worker setup guide
- API documentation
- Contributing guidelines
- MIT License

### Performance
- Initial load: 0.065s for 30 images (pagination)
- Face detection: 2-5 sec/image (CPU), 0.01-0.02 sec/image (GPU)
- Database optimized for 50k+ images
- Resource limits for Docker containers

## [Unreleased]

### Planned
- Thumbnail generation for faster loading
- Advanced search (date, location, people)
- Bulk operations (multi-select, batch assignment)
- Multi-user support with authentication
- Album creation and management
- Video support
- Mobile app (React Native)

---

[1.0.0]: https://github.com/rnagarajanmca/ninav/releases/tag/v1.0.0
