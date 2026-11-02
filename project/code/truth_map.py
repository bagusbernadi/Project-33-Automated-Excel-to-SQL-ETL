"""Pemetaan baris data file Excel (urutan seq) ke baris bersih asal (truth_production.csv). Hanya dipakai skrip validasi dan test.
Generator menyisipkan salinan baris ganda tepat setelah baris asalnya, jadi posisi baris asal i bergeser sebanyak jumlah baris ganda sebelum i."""
import pandas as pd

from common import ISSUES_CSV, TRUTH_CSV


def load_truth():
    t = pd.read_csv(TRUTH_CSV)
    t["idx"] = t.groupby("file").cumcount()
    return t


def load_issues():
    return pd.read_csv(ISSUES_CSV)


def seq_map(n_clean, dup_idx):
    """Daftar (indeks_asal, salinan?) menurut urutan baris di file."""
    dups, out = set(dup_idx), []
    for i in range(n_clean):
        out.append((i, False))
        if i in dups:
            out.append((i, True))
    return out


def file_maps(issues, n_clean=120):
    """dict nama file -> daftar (indeks_asal, salinan?)."""
    dup = issues[issues.issue_type == "duplicate_row"].groupby("file").body_row_index.apply(list).to_dict()
    return {f: seq_map(n_clean, dup.get(f, [])) for f in issues.file.unique()}
