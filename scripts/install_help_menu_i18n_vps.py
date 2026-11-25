"""Install localized help and merge its keys into the VPS interface catalogs."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

MENU = Path("messages/help_menu.py")
BUNDLE = Path("messages/help_menu_locales.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    source = Path(__file__).resolve().parents[1]
    target = args.target.resolve()
    if not (target / MENU).is_file() or not (target / "i18n/__init__.py").is_file():
        parser.exit(1, "A VPS precisa ter o menu do PR #75 e o sistema i18n instalados.\n")

    changes = {MENU: (source / MENU).read_bytes(), BUNDLE: (source / BUNDLE).read_bytes()}
    compile(changes[MENU], str(MENU), "exec")
    bundle = json.loads(changes[BUNDLE])
    catalogs = Path("i18n/locales")
    for path in sorted((target / catalogs).glob("*.json")):
        if path.stem not in bundle:
            continue
        catalog = json.loads(path.read_bytes())
        catalog.update(bundle[path.stem])
        changes[path.relative_to(target)] = (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode()
    if (catalogs / "en.json") not in changes:
        parser.exit(1, "Catálogo inglês do bot não encontrado.\n")

    changes = {
        path: content for path, content in changes.items()
        if not (target / path).exists() or (target / path).read_bytes() != content
    }
    for path in changes:
        print(path)
    if not changes or not args.apply:
        print("Nenhuma alteração pendente." if not changes else "Simulação. Use --apply para instalar.")
        return

    backup = Path(tempfile.mkdtemp(prefix="bot-help-i18n-", dir=target.parent))
    for path in changes:
        current = target / path
        if current.exists():
            saved = backup / path
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(current, saved)

    print(f"Backup salvo em {backup}", flush=True)
    written = []
    try:
        for path, content in changes.items():
            current = target / path
            with tempfile.NamedTemporaryFile(dir=current.parent, delete=False) as handle:
                staged = Path(handle.name)
                try:
                    handle.write(content)
                    handle.flush()
                    staged.chmod(current.stat().st_mode & 0o777 if current.exists() else 0o644)
                    staged.replace(current)
                    written.append(path)
                finally:
                    staged.unlink(missing_ok=True)
    except BaseException:
        for path in reversed(written):
            if (backup / path).is_file():
                shutil.copy2(backup / path, target / path)
            else:
                (target / path).unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
