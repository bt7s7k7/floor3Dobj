#!/usr/bin/env python3
"""
Test script for AI Floorplan Service
"""

import requests
import os
import time

# Configuration
API_BASE_URL = "http://localhost:8081"  # Through nginx
# API_BASE_URL = "http://localhost:5001"  # Direct to Flask

def test_health_check():
    """Test health check endpoint"""
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

def test_simple_processing():
    """Test simple processing endpoint"""
    print("\n🔍 Testing simple processing...")
    
    # Use example image
    test_image = "Images/Examples/example4.png"
    
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        return False
    
    try:
        print(f"📤 Uploading {test_image}...")
        
        with open(test_image, 'rb') as f:
            files = {'image': f}
            
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/process-simple",
                files=files,
                timeout=300  # 5 minutes
            )
            processing_time = time.time() - start_time
        
        if response.status_code == 200:
            # Save the result
            output_file = f"test_result_{int(time.time())}.gltf"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Processing successful!")
            print(f"   Processing time: {processing_time:.1f}s")
            print(f"   Output file: {output_file}")
            print(f"   File size: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ Processing failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Processing error: {e}")
        return False

def test_full_processing():
    """Test full processing endpoint (returns ZIP)"""
    print("\n🔍 Testing full processing...")
    
    test_image = "Images/Examples/example4.png"
    
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        return False
    
    try:
        print(f"📤 Uploading {test_image} for full processing...")
        
        with open(test_image, 'rb') as f:
            files = {'image': f}
            
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/process-floorplan",
                files=files,
                timeout=300  # 5 minutes
            )
            processing_time = time.time() - start_time
        
        if response.status_code == 200:
            # Save the result ZIP
            output_file = f"test_result_full_{int(time.time())}.zip"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Full processing successful!")
            print(f"   Processing time: {processing_time:.1f}s")
            print(f"   Output ZIP: {output_file}")
            print(f"   File size: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ Full processing failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Full processing error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 AI Floorplan Service Test Suite")
    print("=" * 50)
    
    results = []
    
    # Test 1: Health check
    results.append(test_health_check())
    
    # Test 2: Simple processing
    if results[0]:  # Only if health check passed
        results.append(test_simple_processing())
    else:
        print("⏭️  Skipping processing tests - service not healthy")
        results.append(False)
    
    # Test 3: Full processing
    if results[0]:  # Only if health check passed
        results.append(test_full_processing())
    else:
        results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Health Check: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"   Simple Processing: {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"   Full Processing: {'✅ PASS' if results[2] else '❌ FAIL'}")
    
    passed = sum(results)
    total = len(results)
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Service is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs for details.")

if __name__ == "__main__":
    main()
