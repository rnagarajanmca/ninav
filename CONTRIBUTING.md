# Contributing to Ninav

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

This project adheres to a code of conduct that all participants are expected to follow. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Docker version, etc.)
   - Screenshots if applicable

### Suggesting Features

1. **Check discussions** for similar ideas
2. **Create a discussion** or issue describing:
   - The problem your feature would solve
   - Your proposed solution
   - Alternative solutions considered
   - Impact on existing functionality

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** following our coding standards
4. **Write/update tests** for your changes
5. **Update documentation** as needed
6. **Commit with clear messages** following conventional commits
7. **Push to your fork**: `git push origin feature/your-feature-name`
8. **Create a Pull Request** with a clear description

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (optional)

### Local Setup

```bash
# Clone your fork
git clone https://github.com/rnagarajanmca/ninav.git
cd ninav

# Backend setup
cd backend
python -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

# Run tests
cd ../backend && pytest
cd ../frontend && npm test
```

## Coding Standards

### Python (Backend)

- **Style**: Follow PEP 8
- **Type Hints**: Use type hints for all functions
- **Docstrings**: Use Google-style docstrings for classes and functions
- **Formatting**: Black with line length 100
- **Linting**: Ruff
- **Testing**: Pytest with >80% coverage

Example:
```python
def process_image(image_path: Path, config: Settings) -> List[Face]:
    """Process an image and detect faces.

    Args:
        image_path: Path to the image file
        config: Application settings

    Returns:
        List of detected Face objects

    Raises:
        FileNotFoundError: If image doesn't exist
    """
    # Implementation
```

### TypeScript (Frontend)

- **Style**: Follow Airbnb style guide
- **Typing**: Strict TypeScript, avoid `any`
- **Components**: Functional components with hooks
- **Formatting**: Prettier
- **Linting**: ESLint
- **Testing**: Vitest + React Testing Library

Example:
```typescript
interface ImageCardProps {
  image: Image;
  onSelect: (id: string) => void;
}

export const ImageCard: React.FC<ImageCardProps> = ({ image, onSelect }) => {
  // Implementation
};
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(backend): add batch face detection endpoint

Implement /api/faces/detect-batch endpoint that processes
multiple images in parallel for improved performance.

Closes #123
```

```
fix(frontend): resolve image loading race condition

Update useEffect dependencies to prevent stale state in
ImageGallery component when rapidly switching views.
```

## Testing

### Backend Tests

```bash
cd backend
pytest                    # Run all tests
pytest --cov             # With coverage
pytest -v tests/unit     # Specific directory
```

### Frontend Tests

```bash
cd frontend
npm test                 # Run all tests
npm test -- --coverage   # With coverage
npm test -- ImageCard    # Specific component
```

### Integration Tests

```bash
# Start services
docker compose up -d

# Run integration tests
pytest tests/integration

# Cleanup
docker compose down
```

## Documentation

- Update README.md for user-facing changes
- Update API documentation for endpoint changes
- Add JSDoc/docstrings for new functions
- Update migration guides for breaking changes

## Pull Request Process

1. **Ensure CI passes** (tests, linting, type checking)
2. **Update CHANGELOG.md** with your changes
3. **Request review** from maintainers
4. **Address feedback** promptly
5. **Squash commits** before merge (if requested)

### PR Checklist

- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Commit messages follow convention
- [ ] Code follows style guidelines
- [ ] No console.log or debug code

## Project Structure

```
ninav/
├── backend/          # Python FastAPI backend
│   ├── app/
│   │   ├── api/     # API routes
│   │   ├── models/  # Database models
│   │   ├── services/# Business logic
│   │   └── tests/   # Backend tests
│   └── requirements.txt
│
├── frontend/         # React TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── __tests__/
│   └── package.json
│
└── gpu_worker/      # Optional GPU acceleration
    └── main.py
```

## Need Help?

- 💬 **Discussions**: Ask questions, share ideas
- 📖 **Documentation**: Check docs/ directory
- 🐛 **Issues**: Report bugs or request features

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- README.md (for significant contributions)
- Release notes
- Contributors page

Thank you for contributing! 🎉
