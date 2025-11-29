# dframe.py
import pandas as pd
from pathlib import Path
import numpy as np
import json
import os

# optional image save libraries (used only if raw_image is provided)
try:
    import cv2
except Exception:
    cv2 = None

try:
    import imageio
except Exception:
    imageio = None

# --- CONFIG --- #
# adjust this path if your database folder is elsewhere
path = Path("database")

# canonical (internal) column names we will use
# NOTE: 'eye_template' stores the filename (relative to database/eye_templates) or '' if none
# NOTE: email column removed
VOTER_COLS = [
    'voter_id', 'name', 'gender', 'zone', 'city',
    'age', 'passw', 'hasVoted', 'eye_template'
]
CAND_COLS  = ['sign', 'Name', 'Vote Count']

# subfolders for biometric artifacts (inside database/)
EYE_TEMPLATES_DIR = path / "eye_templates"
EYE_IMAGES_DIR    = path / "eye_images"

# Encryption settings
USE_ENCRYPTION = True   # set False to always use plaintext .npz files
# If USE_ENCRYPTION True, dframe will call crypto_utils helpers. Make sure crypto_utils.py exists.
# Keyring config (used by crypto_utils)
KEYRING_SERVICE = "online_voting_app"
KEYRING_USERNAME = "master_key"

# passphrase fallback salt file path (used if keyring isn't used/available)
SALT_PATH = path / "secret_salt.bin"

# --- Internal helpers for folders & CSVs --- #

def _ensure_dir():
    path.mkdir(parents=True, exist_ok=True)
    EYE_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    EYE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def _read_csv_safe(p: Path) -> pd.DataFrame:
    """Read a CSV and return empty DataFrame if missing."""
    _ensure_dir()
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str).fillna('')

def _normalize_voter_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to canonical set.
    Ensures 'age' and 'eye_template' exist.
    """
    if df.empty:
        return pd.DataFrame(columns=VOTER_COLS)

    # build map from existing columns to canonical names
    col_map = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in ('voter_id', 'voterid', 'id'):
            col_map[col] = 'voter_id'
        elif key in ('name',):
            col_map[col] = 'name'
        elif key in ('gender',):
            col_map[col] = 'gender'
        elif key in ('zone',):
            col_map[col] = 'zone'
        elif key in ('city',):
            col_map[col] = 'city'
        elif key in ('age',):
            col_map[col] = 'age'
        elif key in ('passw', 'pass', 'password'):
            col_map[col] = 'passw'
        elif key in ('hasvoted', 'has_voted', 'voted'):
            col_map[col] = 'hasVoted'
        elif key in ('eye_template', 'eye', 'eye_template_file'):
            col_map[col] = 'eye_template'
        else:
            # keep unknown columns as-is
            col_map[col] = col

    df = df.rename(columns=col_map)
    # ensure canonical columns exist
    for c in VOTER_COLS:
        if c not in df.columns:
            # default values
            if c == 'hasVoted':
                df[c] = 0
            elif c == 'age':
                df[c] = '18'
            else:
                df[c] = ''
    # coerce types
    df['hasVoted'] = df['hasVoted'].replace(['False','false',''], 0)
    df['hasVoted'] = pd.to_numeric(df['hasVoted'], errors='coerce').fillna(0).astype(int)
    # age numeric-ish (keep as string for backward compatibility but try to normalize)
    try:
        df['age'] = pd.to_numeric(df['age'], errors='coerce').fillna(18).astype(int)
    except Exception:
        df['age'] = df['age'].astype(str).fillna('18')
    # ensure eye_template is string
    df['eye_template'] = df['eye_template'].fillna('').astype(str)
    return df[VOTER_COLS]

def _write_voter_df(df: pd.DataFrame):
    p = path / 'voterList.csv'
    _ensure_dir()
    df.to_csv(p, index=False)

def _ensure_voter_file():
    p = path / 'voterList.csv'
    _ensure_dir()
    if not p.exists() or p.stat().st_size == 0:
        pd.DataFrame(columns=VOTER_COLS).to_csv(p, index=False)

# ----------------- Public (existing) functions ----------------- #

def count_reset():
    """Reset hasVoted in voterList and Vote Count in cand_list."""
    _ensure_voter_file()
    # voters
    vfile = path/'voterList.csv'
    df_v = _read_csv_safe(vfile)
    df_v = _normalize_voter_df(df_v)
    df_v['hasVoted'] = 0
    _write_voter_df(df_v)

    # candidates
    cfile = path/'cand_list.csv'
    df_c = _read_csv_safe(cfile)
    if df_c.empty:
        # create with expected columns if missing
        pd.DataFrame(columns=CAND_COLS).to_csv(cfile, index=False)
        return
    # ensure Vote Count column exists and reset
    if 'Vote Count' not in df_c.columns:
        df_c['Vote Count'] = 0
    df_c['Vote Count'] = pd.to_numeric(df_c['Vote Count'], errors='coerce').fillna(0).astype(int)
    df_c['Vote Count'] = 0
    df_c.to_csv(cfile, index=False)


def reset_voter_list():
    """Replace voterList.csv with empty file (canonical headers)."""
    _ensure_dir()
    pd.DataFrame(columns=VOTER_COLS).to_csv(path/'voterList.csv', index=False)


def reset_cand_list():
    _ensure_dir()
    pd.DataFrame(columns=CAND_COLS).to_csv(path/'cand_list.csv', index=False)


def verify(vid, passw):
    """
    Return True if (voter_id, passw) match a row.
    passw is compared exactly to stored value (no hashing here).
    """
    df = _read_csv_safe(path/'voterList.csv')
    if df.empty:
        return False
    df = _normalize_voter_df(df)
    matched = df[(df['voter_id'].astype(str) == str(vid)) & (df['passw'].astype(str) == str(passw))]
    return not matched.empty


def isEligible(vid):
    """
    True if voter exists and hasVoted == 0
    """
    df = _read_csv_safe(path/'voterList.csv')
    if df.empty:
        return False
    df = _normalize_voter_df(df)
    row = df[df['voter_id'].astype(str) == str(vid)]
    if row.empty:
        return False
    return int(row['hasVoted'].iloc[0]) == 0


def vote_update(sign, vid):
    """
    Increment candidate Vote Count where Sign==sign and mark voter hasVoted=1.
    Returns True on success.
    """
    # check eligibility first
    if not isEligible(vid):
        return False

    # update candidate file
    cfile = path/'cand_list.csv'
    df_c = _read_csv_safe(cfile)
    if df_c.empty:
        return False
    # ensure Vote Count col
    if 'Vote Count' not in df_c.columns:
        df_c['Vote Count'] = 0
    df_c['Vote Count'] = pd.to_numeric(df_c['Vote Count'], errors='coerce').fillna(0).astype(int)

    mask = df_c['sign'].astype(str) == str(sign)
    if not mask.any():
        return False

    df_c.loc[mask, 'Vote Count'] = df_c.loc[mask, 'Vote Count'] + 1
    df_c.to_csv(cfile, index=False)

    # mark voter hasVoted
    vfile = path/'voterList.csv'
    df_v = _read_csv_safe(vfile)
    df_v = _normalize_voter_df(df_v)
    voter_mask = df_v['voter_id'].astype(str) == str(vid)
    if not voter_mask.any():
        return False
    df_v.loc[voter_mask, 'hasVoted'] = 1
    _write_voter_df(df_v)
    return True


def show_result():
    """Return dict Sign -> Vote Count (int)."""
    cfile = path/'cand_list.csv'
    df_c = _read_csv_safe(cfile)
    if df_c.empty or 'sign' not in df_c.columns or 'Vote Count' not in df_c.columns:
        return {}
    df_c['Vote Count'] = pd.to_numeric(df_c['Vote Count'], errors='coerce').fillna(0).astype(int)
    return { str(r['sign']): int(r['Vote Count']) for _, r in df_c.iterrows() }


def taking_data_voter(name, gender, zone, city, passw, age=18):
    """
    Add a new voter and return voter_id.
    Signature: name, gender, zone, city, passw, age=18
    """

    _ensure_voter_file()
    vfile = path / 'voterList.csv'
    df_v = _read_csv_safe(vfile)
    df_v = _normalize_voter_df(df_v)

    # Generate new voter_id
    if df_v.empty:
        vid = 10001
    else:
        try:
            last = df_v['voter_id'].iloc[-1]
            vid = int(last) + 1
        except Exception:
            vid = 10001 + len(df_v)

    # Build new row
    new_row = {
        'voter_id': vid,
        'name': name,
        'gender': gender,
        'zone': zone,
        'city': city,
        'age': int(age) if age is not None else 18,
        'passw': passw,
        'hasVoted': 0,
        'eye_template': ''
    }

    # Append
    df_v = pd.concat([df_v, pd.DataFrame([new_row])], ignore_index=True)
    _write_voter_df(df_v)
    return vid

# ----------------- Eye template helpers (encryption-aware) ----------------- #

# Attempt to import crypto utilities (optional)
_crypto_ok = False
try:
    from crypto_utils import (
        get_key_from_keyring,
        encode_key_b64,
        decode_key_b64,
        encrypt_bytes_aes_gcm,
        decrypt_bytes_aes_gcm,
        derive_key_from_passphrase,
        generate_key,
        store_key_in_keyring,
        get_key_from_keyring
    )
    _crypto_ok = True
except Exception:
    _crypto_ok = False

def _template_basename_for_vid(vid, encrypted: bool):
    """Return file base name (no directory) for a given voter id."""
    if encrypted:
        return f"{vid}.enc"
    else:
        return f"{vid}.npz"

def _image_filename_for_vid(vid):
    return f"{vid}.png"

def _get_master_key_interactive() -> bytes:
    """
    Return key bytes.
    - Prefer OS keyring via crypto_utils.get_key_from_keyring
    - Fallback to passphrase-derived key using SALT_PATH
    Raises RuntimeError if no key available.
    """
    if not USE_ENCRYPTION:
        raise RuntimeError("Encryption disabled by configuration (USE_ENCRYPTION=False)")

    if _crypto_ok:
        # try keyring
        key = get_key_from_keyring(KEYRING_SERVICE, KEYRING_USERNAME)
        if key is not None:
            return key
        # else fallback to passphrase-derived key
        if not SALT_PATH.exists():
            raise RuntimeError(f"Master key not in keyring and salt file not found at {SALT_PATH}. Create salt or store key in keyring.")
        salt = SALT_PATH.read_bytes()
        import getpass
        passphrase = getpass.getpass("Enter biometric passphrase (used to derive key): ")
        return derive_key_from_passphrase(passphrase, salt)
    else:
        raise RuntimeError("Crypto utilities not available. Install crypto_utils.py and required packages.")

def save_encrypted_template(voter_id, descriptors: np.ndarray):
    """
    Encrypt and save descriptors for voter_id.
    If encryption available and configured, writes database/eye_templates/<vid>.enc (binary).
    If encryption is not enabled or fails, fallback to plaintext .npz.
    Updates voterList.csv 'eye_template' column accordingly.
    """
    _ensure_dir()
    if descriptors is None:
        return False

    if USE_ENCRYPTION and _crypto_ok:
        # serialize descriptors to bytes
        from io import BytesIO
        bio = BytesIO()
        np.savez_compressed(bio, descriptors=descriptors)
        plain_bytes = bio.getvalue()
        # get key
        try:
            key = _get_master_key_interactive()
        except Exception as e:
            print("Encryption key unavailable:", e)
            # fallback to plaintext save
            return _save_plain_template(voter_id, descriptors)

        # encrypt
        try:
            nonce, ciphertext = encrypt_bytes_aes_gcm(key, plain_bytes)
            out_path = EYE_TEMPLATES_DIR / _template_basename_for_vid(voter_id, encrypted=True)
            with open(out_path, "wb") as f:
                f.write(nonce)
                f.write(ciphertext)
            # update CSV pointer
            set_eye_template_filename(voter_id, out_path.name)
            return True
        except Exception as e:
            print("Failed to encrypt/save template:", e)
            return _save_plain_template(voter_id, descriptors)
    else:
        # encryption not enabled or crypto not available: plaintext save
        return _save_plain_template(voter_id, descriptors)

def _save_plain_template(voter_id, descriptors: np.ndarray):
    """Save descriptors as plaintext .npz (fallback)."""
    _ensure_dir()
    try:
        fname = _template_basename_for_vid(voter_id, encrypted=False)
        fpath = EYE_TEMPLATES_DIR / fname
        np.savez_compressed(fpath, descriptors=descriptors)
        set_eye_template_filename(voter_id, fpath.name)
        return True
    except Exception as e:
        print("Failed to save plaintext template:", e)
        return False

def load_encrypted_template(voter_id):
    """
    Load and decrypt the template for voter_id. Returns descriptors numpy array or None.
    If encrypted file exists and decrypts successfully, returns descriptors.
    Else returns None.
    """
    _ensure_dir()
    enc_path = EYE_TEMPLATES_DIR / _template_basename_for_vid(voter_id, encrypted=True)
    if not enc_path.exists():
        return None
    if not (USE_ENCRYPTION and _crypto_ok):
        print("Encryption requested but crypto not available; cannot decrypt:", enc_path)
        return None
    data = enc_path.read_bytes()
    if len(data) < 12:
        print("Encrypted file corrupted/too small:", enc_path)
        return None
    nonce = data[:12]
    ciphertext = data[12:]
    try:
        key = _get_master_key_interactive()
        plain = decrypt_bytes_aes_gcm(key, nonce, ciphertext)
    except Exception as e:
        print("Decryption/auth failed:", e)
        return None
    # load numpy array from bytes
    from io import BytesIO
    bio = BytesIO(plain)
    try:
        npz = np.load(bio, allow_pickle=True)
        if 'descriptors' in npz.files:
            return npz['descriptors']
        elif 'arr_0' in npz.files:
            return npz['arr_0']
        else:
            return None
    except Exception as e:
        print("Failed to parse decrypted numpy archive:", e)
        return None

def _load_plain_template(voter_id):
    """Load plaintext .npz descriptor file if present."""
    _ensure_dir()
    fpath = EYE_TEMPLATES_DIR / _template_basename_for_vid(voter_id, encrypted=False)
    if not fpath.exists():
        return None
    try:
        npz = np.load(fpath, allow_pickle=True)
        if 'descriptors' in npz.files:
            return npz['descriptors']
        elif 'arr_0' in npz.files:
            return npz['arr_0']
        else:
            return None
    except Exception as e:
        print("Failed to load plaintext template:", e)
        return None

def save_eye_template(voter_id, descriptors, raw_image=None):
    """
    Public API expected by register_with_eye.py
    - Saves encrypted template if configured, otherwise plaintext .npz.
    - Saves raw_image (best-effort) to database/eye_images/<vid>.png (unencrypted).
    - Updates voterList.csv 'eye_template' to stored filename.
    Returns True on success, False otherwise.
    """
    ok = False
    try:
        ok = save_encrypted_template(voter_id, descriptors)
    except Exception as e:
        print("save_encrypted_template call failed:", e)
        ok = False

    if not ok:
        # fallback to plaintext save
        ok = _save_plain_template(voter_id, descriptors)

    # save raw image if provided
    if raw_image is not None:
        try:
            imgname = _image_filename_for_vid(voter_id)
            imgpath = EYE_IMAGES_DIR / imgname
            if cv2 is not None:
                # cv2.imwrite expects BGR or grayscale; if array is grayscale it's fine
                cv2.imwrite(str(imgpath), raw_image)
            elif imageio is not None:
                imageio.imwrite(str(imgpath), raw_image)
            else:
                # fallback: save as npz
                np.savez_compressed(imgpath.with_suffix(".npz"), image=raw_image)
        except Exception as e:
            print("Warning: failed to save raw image:", e)

    return ok

def load_eye_template(voter_id):
    """
    Public API expected by voterlogin_with_eye.py
    - Attempts to load & decrypt descriptors using load_encrypted_template (reads <vid>.enc)
    - If encrypted loader isn't available or fails, attempts plaintext .npz load for backward compatibility.
    Returns descriptors numpy array or None.
    """
    # try encrypted loader first if enabled
    if USE_ENCRYPTION:
        try:
            des = load_encrypted_template(voter_id)
            if des is not None:
                return des
        except Exception as e:
            print("Encrypted load failed:", e)
            # fall through to plaintext load

    # fallback to plaintext .npz (legacy)
    return _load_plain_template(voter_id)

def get_eye_template_path(voter_id):
    """Return the full path (string) to the template file if exists, else None."""
    _ensure_dir()
    # prefer encrypted file
    enc = EYE_TEMPLATES_DIR / _template_basename_for_vid(voter_id, encrypted=True)
    if enc.exists():
        return str(enc)
    plain = EYE_TEMPLATES_DIR / _template_basename_for_vid(voter_id, encrypted=False)
    if plain.exists():
        return str(plain)
    return None

def has_eye_template(voter_id):
    """True if we have a saved template for the voter."""
    return get_eye_template_path(voter_id) is not None

def set_eye_template_filename(voter_id, filename):
    """
    Update voterList.csv and set 'eye_template' column for the voter to filename.
    filename should be just the basename (e.g. '10001.enc' or '10001.npz') or ''.
    """
    _ensure_voter_file()
    vfile = path/'voterList.csv'
    df_v = _read_csv_safe(vfile)
    df_v = _normalize_voter_df(df_v)
    mask = df_v['voter_id'].astype(str) == str(voter_id)
    if not mask.any():
        return False
    df_v.loc[mask, 'eye_template'] = filename if filename else ''
    _write_voter_df(df_v)
    return True

def get_voter_row(voter_id):
    """Return dict of voter row (canonical columns) or None."""
    df_v = _read_csv_safe(path/'voterList.csv')
    if df_v.empty:
        return None
    df_v = _normalize_voter_df(df_v)
    row = df_v[df_v['voter_id'].astype(str) == str(voter_id)]
    if row.empty:
        return None
    return row.iloc[0].to_dict()

# ----------------- Admin helpers ----------------- #

def list_voters():
    """Return normalized DataFrame of voters"""
    _ensure_voter_file()
    df_v = _read_csv_safe(path/'voterList.csv')
    return _normalize_voter_df(df_v)

def delete_template_files(voter_id):
    """
    Delete template and raw image for voter_id, and clear CSV pointer.
    """
    tpl = get_eye_template_path(voter_id)
    if tpl:
        try:
            os.remove(tpl)
        except Exception as e:
            print("Warning: failed to remove template file:", e)
    # remove raw image
    imgp = EYE_IMAGES_DIR / _image_filename_for_vid(voter_id)
    if imgp.exists():
        try:
            os.remove(imgp)
        except Exception as e:
            print("Warning: failed to remove raw image:", e)
    # clear CSV pointer
    set_eye_template_filename(voter_id, '')
    return True
