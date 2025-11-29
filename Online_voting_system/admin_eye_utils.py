# admin_eye_utils.py
import dframe as df
from pathlib import Path
import argparse
import os
import numpy as np

def list_templates():
    # read voterList and show who has templates
    v = df._read_csv_safe(Path("database")/'voterList.csv')
    v = df._normalize_voter_df(v)
    print("VoterID | Name | HasTemplate | TemplateFile")
    for _, row in v.iterrows():
        vid = row['voter_id']
        name = row['name']
        tmpl = row.get('eye_template', '') if 'eye_template' in row else ''
        has = 'YES' if tmpl else 'NO'
        print(f"{vid} | {name} | {has} | {tmpl}")

def delete_template(voter_id):
    p = df.get_eye_template_path(voter_id)
    if p is None:
        print("Template not found for", voter_id)
        return
    try:
        os.remove(p)
        # remove raw image if exists
        raw = Path("database")/ "eye_images" / f"{voter_id}.png"
        if raw.exists():
            os.remove(raw)
        # clear csv pointer
        df.set_eye_template_filename(voter_id, '')
        print("Deleted template for", voter_id)
    except Exception as e:
        print("Failed to delete template:", e)

def show_path(voter_id):
    p = df.get_eye_template_path(voter_id)
    if p:
        print("Template path:", p)
    else:
        print("No template found for", voter_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Admin utilities for eye templates")
    parser.add_argument('--list', action='store_true', help='List voters and templates')
    parser.add_argument('--delete', help='Delete template for voter id')
    parser.add_argument('--show', help='Show template path for voter id')
    args = parser.parse_args()

    if args.list:
        list_templates()
    elif args.delete:
        delete_template(args.delete)
    elif args.show:
        show_path(args.show)
    else:
        parser.print_help()
