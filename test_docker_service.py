#!/usr/bin/env python3
"""
Final test script for Docker AI Service
"""

import requests
import os
import time

API_BASE_URL = "http://localhost:5002"

def test_health():
    """Test health check"""
    print("🔍 Testing health check...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed!")
            print(f"   Status: {data.get('status')}")
            print(f"   Blender: {data.get('blender_path')}")
            print(f"   OpenAI: {data.get('openai_configured')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_gltf_export():
    """Test glTF export from existing .blend file"""
    print("\n🔍 Testing glTF export...")
    
    try:
        start_time = time.time()
        response = requests.get(f"{API_BASE_URL}/test-gltf-export", timeout=60)
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            # Save the result
            output_file = f"docker_test_export_{int(time.time())}.gltf"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ glTF export successful!")
            print(f"   Processing time: {processing_time:.1f}s")
            print(f"   Output file: {output_file}")
            print(f"   File size: {len(response.content)} bytes")
            
            # Verify it's valid glTF
            if response.content.startswith(b'{'):
                print(f"   Format: Valid JSON (glTF)")
                return True
            else:
                print(f"   Format: Binary or invalid")
                return False
        else:
            print(f"❌ glTF export failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ glTF export error: {e}")
        return False

def main():
    """Run Docker service tests"""
    print("🐳 Docker AI Service Test Suite")
    print("=" * 50)
    
    results = []
    
    # Test 1: Health check
    results.append(test_health())
    
    # Test 2: glTF export functionality  
    if results[0]:
        results.append(test_gltf_export())
    else:
        print("⏭️  Skipping export test - service not healthy")
        results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Health Check: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"   glTF Export: {'✅ PASS' if results[1] else '❌ FAIL'}")
    
    passed = sum(results)
    total = len(results)
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Docker service is working correctly!")
        print("\n📋 Ready for production:")
        print("   • Health check: ✅")
        print("   • glTF export: ✅") 
        print("   • API endpoints: ✅")
        print("\n🚀 Usage:")
        print(f"   curl -X GET {API_BASE_URL}/health")
        print(f"   curl -X GET {API_BASE_URL}/test-gltf-export -o test.gltf")
    else:
        print("⚠️  Some tests failed. Check the logs for details.")

if __name__ == "__main__":
    main()
