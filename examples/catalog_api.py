# Catalog API Examples

This directory contains working, runnable examples for the Catalog API endpoints.

## Prerequisites

These examples assume you have PythonDepot running locally:

```bash
# From the project root directory
cd python-depot

# Start the development server
uvicorn src.app:app --reload
```

## Example 1: Basic Package Operations

This example demonstrates basic CRUD operations for packages.

```python
import httpx
import asyncio
from typing import Dict, Any

async def basic_package_operations():
    """Example: Basic package operations using Catalog API."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("🚀 Starting Catalog API Examples")
        print("=" * 50)
        
        # 1. List all packages
        print("\n1. 📋 Listing all packages...")
        response = await client.get(f"{base_url}/api/v1/packages/")
        packages_data = response.json()
        print(f"Found {packages_data['total']} packages")
        
        # 2. Get specific package (requests exists by default in tests)
        print("\n2. 🔍 Getting package 'requests'...")
        response = await client.get(f"{base_url}/api/v1/packages/requests")
        package_data = response.json()
        print(f"Package 'requests' found: {package_data['found']}")
        
        # 3. Create new package
        print("\n3. ➕ Creating new package...")
        new_package = {
            "name": "mcp-sdk-demo",
            "summary": "Model Context Protocol SDK for demonstration",
            "description": "A Python SDK demonstrating MCP integration with FastAPI and modern Python practices.",
            "homepage": "https://github.com/modelcontextprotocol/sdk-python",
            "repository": "https://github.com/modelcontextprotocol/sdk-python",
            "author": "Model Context Protocol Team",
            "license": "MIT",
            "latest_version": "0.1.0"
        }
        response = await client.post(f"{base_url}/api/v1/packages/", json=new_package)
        create_result = response.json()
        print(f"Created package: {create_result['status']} (ID: {create_result.get('package', {}).get('id', 'N/A')})")
        
        # 4. Update the newly created package
        print("\n4. 📝 Updating package 'mcp-sdk-demo'...")
        update_data = {
            "summary": "Updated MCP SDK summary",
            "latest_version": "0.1.1"
        }
        response = await client.put(f"{base_url}/api/v1/packages/mcp-sdk-demo", json=update_data)
        update_result = response.json()
        print(f"Updated package: {update_result['status']}")
        
        # 5. Get the updated package
        print("\n5. 🔄 Verifying updated package...")
        response = await client.get(f"{base_url}/api/v1/packages/mcp-sdk-demo")
        updated_package = response.json()
        print(f"Updated package found: {updated_package['found']}")
        
        # 6. Delete the package (cleanup)
        print("\n6. 🗑️ Deleting created package...")
        response = await client.delete(f"{base_url}/api/v1/packages/mcp-sdk-demo")
        delete_result = response.json()
        print(f"Deleted package: {delete_result['status']}")
        
        print("\n✅ All catalog operations completed successfully!")
        print("\n📊 Summary of operations:")
        print("  - Listed all packages")
        print("  - Retrieved 'requests' package")
        print("  - Created 'mcp-sdk-demo' package")
        print("  - Updated package metadata")
        print("  - Deleted created package (cleanup)")

if __name__ == "__main__":
    asyncio.run(basic_package_operations())
```