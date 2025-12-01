import streamlit as st
import pandas as pd
from io import BytesIO

st.title("🎓 ARank-Based Allotment (AIQ-excluded, No Reservation)")

# ----------------------------------------------------
# UNIVERSAL FILE READER (NO openpyxl REQUIRED)
# ----------------------------------------------------
def read_any(file):
    name = file.name.lower()

    if name.endswith(".csv"):
        file.seek(0)
        return pd.read_csv(file, encoding="ISO-8859-1")

    if name.endswith(".xlsx") or name.endswith(".xls"):
        file.seek(0)
        try:
            xls = pd.ExcelFile(file, engine="odf")
            return pd.read_excel(xls)
        except:
            file.seek(0)
            return pd.read_csv(file, encoding="ISO-8859-1")

    file.seek(0)
    return pd.read_csv(file, encoding="ISO-8859-1")


# ----------------------------------------------------
# UPLOAD FILES
# ----------------------------------------------------
cand_file = st.file_uploader("1️⃣ Candidates File (with ARank, Category, AIQ)", type=["csv","xlsx"])
seat_file = st.file_uploader("2️⃣ Seat Matrix File", type=["csv","xlsx"])
opt_file  = st.file_uploader("3️⃣ Option Entry File", type=["csv","xlsx"])

if cand_file and seat_file and opt_file:

    cand = read_any(cand_file)
    seats = read_any(seat_file)
    opts = read_any(opt_file)

    st.success("Files loaded. Processing...")

    # --------------------------------------
    # CLEAN SEAT MATRIX
    # --------------------------------------
    for col in ["grp","typ","college","course","SEAT"]:
        if col not in seats.columns:
            st.error(f"Seat file missing column: {col}")
            st.stop()

    for col in ["grp","typ","college","course"]:
        seats[col] = seats[col].astype(str).str.upper().str.strip()

    seats["SEAT"] = pd.to_numeric(seats["SEAT"], errors="ignore").fillna(0).astype(int)

    seat_map = {}
    for _, r in seats.iterrows():
        key = (r["grp"], r["typ"], r["college"], r["course"])
        seat_map[key] = seat_map.get(key, 0) + r["SEAT"]

    # --------------------------------------
    # CLEAN OPTIONS
    # --------------------------------------
    opts["Optn"] = opts["Optn"].astype(str).str.upper().str.strip()
    opts = opts[(opts["OPNO"] != 0) & (opts["ValidOption"].astype(str).str.upper() == "Y")]
    opts = opts.sort_values(["RollNo","OPNO"])

    opts["RollNo"] = pd.to_numeric(opts["RollNo"], errors="coerce").astype("Int64")

    # --------------------------------------
    # CLEAN CANDIDATES
    # --------------------------------------
    if "ARank" not in cand.columns:
        st.error("Candidate file missing ARank")
        st.stop()

    cand["RollNo"] = pd.to_numeric(cand["RollNo"], errors="coerce").astype("Int64")
    cand["ARank"] = pd.to_numeric(cand["ARank"], errors="coerce").fillna(9999999).astype(int)

    # Sort by ARank
    cand = cand.sort_values("ARank")

    # --------------------------------------
    # OPTN DECODER
    # --------------------------------------
    def decode_opt(opt):
        opt = opt.strip().upper()
        if len(opt) < 7:
            return None
        grp = opt[0]
        typ = opt[1]
        course = opt[2:4]
        college = opt[4:7]
        return grp, typ, course, college

    # --------------------------------------
    # RUN ALLOTMENT
    # --------------------------------------
    allotments = []

    for _, c in cand.iterrows():
        roll = int(c["RollNo"])
        arank = int(c["ARank"])
        category = c.get("Category", "")

        # AIQ = Y means not eligible
        if "AIQ" in c and str(c["AIQ"]).upper().strip() == "Y":
            continue

        # Fetch options
        c_opts = opts[opts["RollNo"] == roll]
        if c_opts.empty:
            continue

        for _, op in c_opts.iterrows():
            dec = decode_opt(op["Optn"])
            if not dec:
                continue

            og, otyp, ocourse, oclg = dec
            key = (og, otyp, oclg, ocourse)

            if seat_map.get(key, 0) > 0:
                seat_map[key] -= 1
                allotments.append({
                    "RollNo": roll,
                    "ARank": arank,
                    "Category": category,
                    "grp": og,
                    "typ": otyp,
                    "College": oclg,
                    "Course": ocourse,
                    "OptionNo": op["OPNO"]
                })
                break

    # --------------------------------------
    # OUTPUT
    # --------------------------------------
    df = pd.DataFrame(allotments)

    st.subheader("🟩 Allotment Result")
    st.write(f"Total Allotted: {len(df)}")

    if len(df) > 0:
        st.dataframe(df)

        buf = BytesIO()
        df.to_csv(buf, index=False)
        buf.seek(0)

        st.download_button(
            "⬇️ Download Allotment CSV",
            buf,
            "allotment_result.csv",
            "text/csv"
        )
    else:
        st.warning("No allotments.")
