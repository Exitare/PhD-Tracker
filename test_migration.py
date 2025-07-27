#!/usr/bin/env python3
"""
Test script to verify Quart migration is working correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_app_creation():
    """Test that the Quart app can be created successfully."""
    try:
        from src import create_app
        
        print("📦 Testing app creation...")
        app = create_app()
        
        if app:
            print("✅ App created successfully!")
            print(f"   App type: {type(app)}")
            return True
        else:
            print("❌ App creation returned None")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you've installed the new requirements:")
        print("   pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error creating app: {e}")
        return False

async def test_route_imports():
    """Test that route modules can be imported."""
    route_modules = [
        'dashboard', 'project', 'notes', 'sub_project', 'milestone', 
        'auth', 'home', 'about', 'revision', 'account', 'webhooks',
        'journal', 'venue', 'academia', 'admin', 'plans', 'showcase'
    ]
    
    print("\n📋 Testing route imports...")
    failed_imports = []
    
    for module_name in route_modules:
        try:
            module = __import__(f'src.routes.{module_name}', fromlist=['bp'])
            if hasattr(module, 'bp'):
                print(f"✅ {module_name}: imported successfully")
            else:
                print(f"⚠️  {module_name}: imported but no 'bp' blueprint found")
                failed_imports.append(module_name)
        except ImportError as e:
            print(f"❌ {module_name}: import failed - {e}")
            failed_imports.append(module_name)
        except Exception as e:
            print(f"❌ {module_name}: error - {e}")
            failed_imports.append(module_name)
    
    if failed_imports:
        print(f"\n⚠️  {len(failed_imports)} modules had import issues: {', '.join(failed_imports)}")
        return False
    else:
        print(f"\n✅ All {len(route_modules)} route modules imported successfully!")
        return True

async def test_extensions():
    """Test that extensions can be imported."""
    print("\n🔧 Testing extensions...")
    
    try:
        from src.extensions import csrf, mail
        print("✅ Extensions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Extension import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Extension error: {e}")
        return False

async def test_forms():
    """Test that forms can be imported."""
    print("\n📝 Testing forms...")
    
    form_modules = ['account_forms', 'contact_form']
    failed_forms = []
    
    for form_module in form_modules:
        try:
            __import__(f'src.forms.{form_module}')
            print(f"✅ {form_module}: imported successfully")
        except ImportError as e:
            print(f"❌ {form_module}: import failed - {e}")
            failed_forms.append(form_module)
        except Exception as e:
            print(f"❌ {form_module}: error - {e}")
            failed_forms.append(form_module)
    
    if failed_forms:
        print(f"\n⚠️  {len(failed_forms)} form modules had issues: {', '.join(failed_forms)}")
        return False
    else:
        print(f"\n✅ All {len(form_modules)} form modules imported successfully!")
        return True

async def main():
    """Run all tests."""
    print("🧪 Running Quart Migration Tests\n" + "="*50)
    
    tests = [
        ("App Creation", test_app_creation),
        ("Extensions", test_extensions),
        ("Forms", test_forms),
        ("Routes", test_route_imports),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your migration looks good.")
        print("   Next steps:")
        print("   1. Run the app with: python run.py --dev")
        print("   2. Test all routes manually")
        print("   3. Run your existing test suite")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues before proceeding.")
        print("   Check the error messages above for details.")

if __name__ == "__main__":
    asyncio.run(main())
