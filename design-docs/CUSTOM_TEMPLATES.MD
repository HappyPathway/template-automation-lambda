# Custom Template Management

This document outlines approaches for managing custom GitHub repository templates, including support for subdirectory-based templates.

## Template Sources

### Full Repository Templates
The standard approach where an entire repository is used as a template.

### Subdirectory Templates
Allows using a specific subdirectory from a template repository, enabling:
- Modular template organization
- Sharing common components
- Granular template selection

## Usage

### Creating from Full Repository

```json
{
    "action": "create",
    "project_name": "my-service",
    "template_settings": {
        "type": "service",
        "environment": "prod",
        "variables": {
            "region": "us-west-2"
        }
    }
}
```

### Creating from Subdirectory

```json
{
    "action": "create",
    "project_name": "my-service",
    "template_settings": {
        "type": "service",
        "environment": "prod",
        "source_path": "templates/microservice",
        "variables": {
            "region": "us-west-2"
        }
    }
}
```

## Template Organization

Example structure for a template repository using subdirectories:

```
template-repository/
├── README.md
├── templates/
│   ├── microservice/           # Template for microservices
│   │   ├── .github/
│   │   │   └── workflows/
│   │   ├── src/
│   │   └── config/
│   ├── terraform-module/       # Template for Terraform modules
│   │   ├── .github/
│   │   └── examples/
│   └── python-package/         # Template for Python packages
│       ├── .github/
│       └── src/
└── common/                     # Shared components
    ├── workflows/
    ├── scripts/
    └── config/
```

## Implementation Details

### Template Copying Logic

1. Validate source path exists in template repository
2. If source path specified:
   - Get contents of specified directory
   - Strip source path prefix from target paths
3. If no source path:
   - Get contents of entire repository
4. Copy files maintaining directory structure
5. Generate and store destroy token

### Error Handling

- Source path validation
- File copy failures
- Permission issues
- Missing files/directories

## Security Considerations

1. **Access Control**: 
   - Template repository access restrictions
   - Source path validation
2. **Content Validation**:
   - File type restrictions
   - Size limits
   - Path traversal prevention

## Best Practices

1. **Template Organization**:
   - Use clear directory structure
   - Include README in each template
   - Document variables and requirements

2. **Subdirectory Usage**:
   - Group related templates
   - Share common components
   - Use consistent naming

3. **Maintenance**:
   - Regular template updates
   - Version tagging
   - Change documentation

## Future Enhancements

1. **Template Composition**:
   - Combine multiple subdirectories
   - Template inheritance
   - Component overrides

2. **Validation**:
   - Template schema validation
   - Required files checking
   - Variable validation

3. **Advanced Features**:
   - Template versioning
   - Hot-reload templates
   - Template discovery API