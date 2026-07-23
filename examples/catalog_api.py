#!/usr/bin/env python3
"""
Catalog API Examples.

Demonstrates package CRUD (create, read, update, delete) operations
using the PythonDepot Catalog API.

Prerequisites:
- PythonDepot server running locally (uvicorn python_depot.api:app --reload)
- httpx library installed
"""

import asyncio

import httpx


async def catalog_examples():
    """Example: Catalog API operations."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("🚀 Starting Catalog API Examples")
        print("=" * 50)

        # 1. List all packages
        print("\n1. 📋 Listing all packages...")
        response = await client.get(f"{base_url}/api/v1/packages/")
        packages_data = response.json()
        print(f"   Found {packages_data['total']} packages")

        # 2. Get a specific package (health report)
        print("\n2. 🔍 Getting health report for 'requests'...")
        response = await client.get(f"{base_url}/api/v1/packages/requests")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            pkg = response.json()
            print(f"   Health score: {pkg.get('health_score')}")
        else:
            print(f"   Response: {response.json()}")

        # 3. Create a new package
        print("\n3. ➕ Creating new package 'mcp-sdk-demo'...")
        new_package = {
            "name": "mcp-sdk-demo",
            "summary": "Model Context Protocol SDK for demonstration",
            "description": "A Python SDK for MCP integration.",
            "homepage": "https://github.com/modelcontextprotocol/sdk-python",
            "repository": "https://github.com/modelcontextprotocol/sdk-python",
            "author": "MCP Team",
            "license": "MIT",
            "latest_version": "0.1.0",
        }
        response = await client.post(
            f"{base_url}/api/v1/packages/", json=new_package
        )
        create_result = response.json()
        print(f"   Status: {create_result['status']}")

        # 4. Update the newly created package
        print("\n4. 📝 Updating package 'mcp-sdk-demo'...")
        update_data = {"summary": "Updated MCP SDK summary", "latest_version": "0.1.1"}
        response = await client.put(
            f"{base_url}/api/v1/packages/mcp-sdk-demo", json=update_data
        )
        update_result = response.json()
        print(f"   Status: {update_result['status']}")

        # 5. Delete the created package (cleanup)
        print("\n5. 🗑️ Deleting created package...")
        response = await client.delete(f"{base_url}/api/v1/packages/mcp-sdk-demo")
        delete_result = response.json()
        print(f"   Status: {delete_result['status']}")

        print("\n✅ All catalog operations completed!")
        print("\n📊 Summary of operations:")
        print("   - Listed all packages")
        print("   - Retrieved package health report")
        print("   - Created 'mcp-sdk-demo' package")
        print("   - Updated package metadata")
        print("   - Deleted created package (cleanup)")


if __name__ == "__main__":
    asyncio.run(catalog_examples())
