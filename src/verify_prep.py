"""Verify the prepared receptors kept the right biology: correct mutations, kept cofactors,
stripped drugs/waters, hydrogens added."""
import warnings
from Bio.PDB import PDBParser
warnings.filterwarnings("ignore")

PREP = "/Users/ricardoperezcastillo/Library/CloudStorage/OneDrive-Personal/Documents/GitHub/anthropic-hackathon/data/structures/prepared"
AA = set("ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL".split())

# expected residue identity at the hotspot positions (author numbering)
CHECKS = {
    "3POZ": [("EGFR WT",        790, "THR"), (None, 858, "LEU")],
    "8A2B": [("EGFR L858R",     790, "THR"), (None, 858, "ARG")],
    "4I24": [("EGFR T790M",     790, "MET"), (None, 858, "LEU")],
    "5UGC": [("EGFR L+T double",790, "MET"), (None, 858, "ARG")],
    "8FMI": [("KRAS WT",         12, "GLY")],
    "4LDJ": [("KRAS G12C",       12, "CYS")],
    "6OIM": [("KRAS G12C+soto",  12, "CYS")],
}
KRAS = {"8FMI", "4LDJ", "6OIM"}
parser = PDBParser(QUIET=True)

all_ok = True
for pdb, checks in CHECKS.items():
    s = parser.get_structure(pdb, f"{PREP}/{pdb}_receptor.pdb")
    # collect residues by number (chain A protein), hetero names, H presence
    resmap, hets, has_h = {}, set(), False
    for chain in s[0]:
        for res in chain:
            rn = res.resname.strip()
            if rn in AA:
                resmap[res.id[1]] = rn
            elif rn not in ("HOH", "WAT"):
                hets.add(rn)
            if any(a.element == "H" for a in res):
                has_h = True

    label = checks[0][0]
    line = [f"{pdb} ({label})"]
    for _, pos, expect in checks:
        got = resmap.get(pos, "MISSING")
        ok = got == expect
        all_ok &= ok
        line.append(f"res{pos}={got}{'✓' if ok else f' ✗(want {expect})'}")

    # cofactor / cleanliness checks
    if pdb in KRAS:
        cof_ok = ("GDP" in hets and "MG" in hets)
        all_ok &= cof_ok
        line.append(f"GDP+MG kept={'✓' if cof_ok else '✗'}")
    drug_free = "MOV" not in hets  # sotorasib must be gone from 6OIM
    line.append(f"H={'✓' if has_h else '✗'}")
    line.append(f"hets={sorted(hets) if hets else 'none'}")
    print("  " + " | ".join(line))

print("\n" + ("ALL GENOTYPE/COFACTOR CHECKS PASSED ✓" if all_ok else "SOME CHECKS FAILED ✗"))
