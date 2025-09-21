#!/usr/bin/env python3
"""
Quick test script for GLB API
"""

import requests
import json
import base64
import time

def test_glb_api():
    """Test GLB API with example image"""
    
    print("🧪 Quick GLB API Test")
    print("=" * 40)
    
    # Test with existing image
    test_image = "Images/Examples/example5.png"
    api_url = "http://localhost:5002/test-glb-export"
    
    print(f"📤 Testing GLB export...")
    
    try:
        # Call API
        response = requests.get(api_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                # Decode GLB
                glb_base64 = data['model']
                glb_data = base64.b64decode(glb_base64)
                
                # Save GLB
                output_file = f"quick_test_{int(time.time())}.glb"
                with open(output_file, 'wb') as f:
                    f.write(glb_data)
                
                metadata = data.get('metadata', {})
                
                print("✅ SUCCESS!")
                print(f"   GLB file: {output_file}")
                print(f"   Size: {len(glb_data):,} bytes")
                print(f"   Base64 chars: {len(glb_base64):,}")
                print(f"   Magic: {glb_data[:4]}")
                print(f"   Timestamp: {metadata.get('timestamp', 'N/A')}")
                
                # Verify GLB
                if glb_data.startswith(b'glTF'):
                    print("   Format: ✅ Valid GLB")
                    return True
                else:
                    print("   Format: ❌ Invalid GLB")
                    return False
            else:
                print(f"❌ API Error: {data.get('error', 'Unknown')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def show_usage():
    """Show usage examples"""
    print("\n" + "=" * 40)
    print("📋 Usage Examples:")
    print()
    print("1. Health check:")
    print("   curl -X GET http://localhost:5002/health")
    print()
    print("2. GLB export test:")
    print("   curl -X GET http://localhost:5002/test-glb-export")
    print()
    print("3. Full workflow (PNG → GLB):")
    print("   curl -X POST -F 'image=@your_image.png' \\")
    print("        http://localhost:5002/process-glb \\")
    print("        -o response.json")
    print()
    print("4. Decode GLB from response:")
    print("   python3 -c \"")
    print("   import json, base64")
    print("   data = json.load(open('response.json'))")
    print("   glb = base64.b64decode(data['model'])")
    print("   open('result.glb', 'wb').write(glb)")
    print("   \"")

if __name__ == "__main__":
    success = test_glb_api()
    show_usage()
    
    if success:
        print("\n🎉 API je funkčná a pripravená na použitie!")
    else:
        print("\n⚠️  Skontrolujte či služba beží: http://localhost:5002/health")
