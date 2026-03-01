import os
import sys
import shutil
# Ensure project root is on sys.path so we can import core modules when run as script
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from core.normalizacao import normalizar_nome_completo

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'arquivos_gerados', 'PGC')


def move_contents(src_dir, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(dest_dir, item)
        if os.path.isdir(s):
            # recursively move
            if os.path.exists(d):
                # merge: move entries inside
                for sub in os.listdir(s):
                    ssub = os.path.join(s, sub)
                    dsub = os.path.join(d, sub)
                    if os.path.exists(dsub):
                        # rename conflicting file/folder
                        base, ext = os.path.splitext(sub)
                        newname = f"{base}_from_credores{ext}"
                        dsub = os.path.join(d, newname)
                    shutil.move(ssub, dsub)
                # after moving inner contents, remove source dir
                try:
                    os.rmdir(s)
                except Exception:
                    pass
            else:
                shutil.move(s, d)
        else:
            if os.path.exists(d):
                base, ext = os.path.splitext(item)
                newname = f"{base}_from_credores{ext}"
                d = os.path.join(dest_dir, newname)
            shutil.move(s, d)


def fix_pgc(pgc_dir):
    found = False
    for name in os.listdir(pgc_dir):
        if name.upper() == 'CREDORES' and os.path.isdir(os.path.join(pgc_dir, name)):
            credores_dir = os.path.join(pgc_dir, name)
            print(f"Found legacy 'CREDORES' in {pgc_dir}, migrating contents...")
            for cred in os.listdir(credores_dir):
                src = os.path.join(credores_dir, cred)
                if not os.path.isdir(src):
                    continue
                # normalized target name
                target_name = normalizar_nome_completo(cred)
                target = os.path.join(pgc_dir, target_name)
                move_contents(src, target)
                # if src now empty, remove it
                try:
                    os.rmdir(src)
                except Exception:
                    pass
            # after moving everything, remove the CREDORES dir if empty
            try:
                os.rmdir(credores_dir)
                print(f"Removed empty {credores_dir}")
            except Exception:
                print(f"Could not remove {credores_dir} (not empty)")
            found = True
    return found


def main(pgc_number=None):
    if pgc_number:
        pgc_path = os.path.join(BASE, str(int(pgc_number) if str(pgc_number).isdigit() else pgc_number))
        if not os.path.isdir(pgc_path):
            print(f"PGC folder not found: {pgc_path}")
            return 2
        changed = fix_pgc(pgc_path)
        print(f"PGC {pgc_number}: migration applied: {changed}")
        return 0

    # global scan
    print(f"Scanning all PGCs under {BASE}")
    any_changed = False
    for pgc in os.listdir(BASE):
        pgc_path = os.path.join(BASE, pgc)
        if not os.path.isdir(pgc_path):
            continue
        changed = fix_pgc(pgc_path)
        any_changed = any_changed or changed
    print(f"Any migrations performed: {any_changed}")
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1:
        sys.exit(main(sys.argv[1]))
    else:
        sys.exit(main())
