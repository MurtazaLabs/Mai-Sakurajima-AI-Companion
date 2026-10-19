"""
Build .mpkg packages for core plugins
"""
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.plugin_manifest import PluginManifest, PluginPermission
from plugins.signing import PluginSigner


def build_plugin_package(plugin_dir: Path, output_dir: Path, signer: PluginSigner | None = None) -> Path:
    """Build a .mpkg package from a plugin directory."""
    manifest_path = plugin_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"No manifest.json in {plugin_dir}")
    
    manifest = PluginManifest.load(manifest_path)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{manifest.name}-{manifest.version}.mpkg"
    
    if signer:
        return signer.create_signed_package(plugin_dir, output_path)
    else:
        # Create unsigned package
        with tempfile.NamedTemporaryFile(suffix=".mpkg", delete=False) as tmp:
            temp_path = Path(tmp.name)
        
        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in plugin_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(plugin_dir)
                        zf.write(file_path, arcname)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(temp_path, output_path)
            return output_path
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise


def build_all_plugins(plugins_root: Path, output_dir: Path, signer: PluginSigner | None = None):
    """Build packages for all plugins in the plugins directory."""
    results = []
    
    for plugin_dir in plugins_root.iterdir():
        if plugin_dir.is_dir() and (plugin_dir / "manifest.json").exists():
            try:
                print(f"Building {plugin_dir.name}...")
                package_path = build_plugin_package(plugin_dir, output_dir, signer)
                print(f"  [OK] {package_path}")
                results.append((plugin_dir.name, package_path))
            except Exception as e:
                print(f"  [FAIL] {plugin_dir.name}: {e}")
                results.append((plugin_dir.name, None))
    
    return results


def create_manifest_for_plugin(name: str, version: str, description: str, author: str,
                                entry_point: str, permissions: dict, hooks: list,
                                tags: list, min_mai_version: str = "1.0.0") -> PluginManifest:
    """Helper to create a manifest for a plugin."""
    return PluginManifest(
        name=name,
        version=version,
        description=description,
        author=author,
        entry_point=entry_point,
        api_version="1.0",
        permissions=PluginPermission(**permissions),
        dependencies=[],
        hooks=hooks,
        min_mai_version=min_mai_version,
        tags=tags,
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build plugin packages")
    parser.add_argument("--plugins-dir", type=Path, default=Path("plugins"), help="Plugins source directory")
    parser.add_argument("--output-dir", type=Path, default=Path("dist/plugins"), help="Output directory for .mpkg files")
    parser.add_argument("--sign", action="store_true", help="Sign packages with generated key")
    parser.add_argument("--key-file", type=Path, help="Private key file for signing")
    
    args = parser.parse_args()
    
    signer = None
    if args.sign:
        if args.key_file and args.key_file.exists():
            signer = PluginSigner.from_private_key_file(args.key_file)
        else:
            signer = PluginSigner()
            # Save key for future use
            key_dir = Path.home() / ".config" / "mai" / "keys"
            key_dir.mkdir(parents=True, exist_ok=True)
            private_key_path = key_dir / "plugin_signing_key.pem"
            public_key_path = key_dir / "plugin_signing_key.pub.pem"
            private_key_path.write_bytes(signer.get_private_key_pem())
            public_key_path.write_bytes(signer.get_public_key_pem())
            print("Generated new signing key:")
            print(f"  Private: {private_key_path}")
            print(f"  Public:  {public_key_path}")
    
    results = build_all_plugins(args.plugins_dir, args.output_dir, signer)
    
    print("\nBuild complete:")
    for name, path in results:
        status = "[OK]" if path else "[FAIL]"
        print(f"  {status} {name}")