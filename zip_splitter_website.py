import streamlit as st
import os, zipfile, shutil
from pathlib import Path
import tempfile

st.set_page_config(page_title="ZIP Splitter", page_icon="📦", layout="centered")

st.title("📦 ZIP Splitter App (Preserves Folder Structure)")
st.write("Upload a ZIP and split it into smaller parts while keeping folders intact.")

# Initialize session state
if "split_done" not in st.session_state:
    st.session_state.split_done = False
if "output_dir" not in st.session_state:
    st.session_state.output_dir = None
if "base_name" not in st.session_state:
    st.session_state.base_name = ""

uploaded = st.file_uploader("Upload your ZIP file", type="zip", disabled=st.session_state.split_done)
max_mb = st.number_input("Max size per part (MB):", 1, 100, 14, disabled=st.session_state.split_done)

# Process ZIP only if not already done
if uploaded and st.button("Split ZIP", disabled=st.session_state.split_done):
    st.info("Processing... please wait ⏳")

    temp_base = Path(tempfile.mkdtemp())
    input_zip = temp_base / uploaded.name
    output_dir = temp_base / "output_parts"
    temp_extract = output_dir / "temp_extracted"

    with open(input_zip, "wb") as f:
        f.write(uploaded.read())

    base_name = Path(uploaded.name).stem
    st.session_state.base_name = base_name
    os.makedirs(temp_extract, exist_ok=True)

    # Extract ZIP safely
    with zipfile.ZipFile(input_zip, 'r') as zip_ref:
        for member in zip_ref.infolist():
            extracted_path = temp_extract / member.filename
            if member.is_dir():
                extracted_path.mkdir(parents=True, exist_ok=True)
            else:
                extracted_path.parent.mkdir(parents=True, exist_ok=True)
                with zip_ref.open(member) as src, open(extracted_path, "wb") as tgt:
                    shutil.copyfileobj(src, tgt)

    # Collect files
    all_files = []
    for root, _, files in os.walk(temp_extract):
        for f in files:
            all_files.append(Path(root) / f)

    max_bytes = max_mb * 1024 * 1024
    part_num, current_size = 1, 0
    part_dir = output_dir / f"{base_name} {part_num}"
    part_dir.mkdir(parents=True, exist_ok=True)

    progress = st.progress(0)
    total_files = len(all_files)

    for i, file_path in enumerate(all_files, start=1):
        file_size = file_path.stat().st_size
        rel_path = file_path.relative_to(temp_extract)

        if current_size + file_size > max_bytes:
            part_num += 1
            part_dir = output_dir / f"{base_name} {part_num}"
            part_dir.mkdir(parents=True, exist_ok=True)
            current_size = 0

        dest = part_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest)
        current_size += file_size
        progress.progress(i / total_files)

    # Create individual part ZIPs
    zip_paths = []
    for i in range(1, part_num + 1):
        folder = output_dir / f"{base_name} {i}"
        zip_path = output_dir / f"{base_name} {i}.zip"
        shutil.make_archive(str(zip_path).replace(".zip", ""), "zip", folder)
        zip_paths.append(zip_path)

    # Save results in session
    st.session_state.split_done = True
    st.session_state.output_dir = output_dir
    st.session_state.zip_paths = zip_paths

    st.success(f"✅ Done! Split into {part_num} parts.")


# If split done — show downloads & actions
if st.session_state.split_done:
    st.subheader("📥 Download Split Parts")

    for z in st.session_state.zip_paths:
        with open(z, "rb") as f:
            st.download_button(
                label=f"⬇️ Download {z.name}",
                data=f,
                file_name=z.name,
                mime="application/zip"
            )

    # Combine all ZIPs into one master ZIP
    all_zip = st.session_state.output_dir / f"{st.session_state.base_name}_AllParts.zip"
    if not all_zip.exists():
        with zipfile.ZipFile(all_zip, "w") as master_zip:
            for z in st.session_state.zip_paths:
                master_zip.write(z, z.name)

    with open(all_zip, "rb") as f:
        st.download_button(
            label=f"📦 Download All Parts ({all_zip.name})",
            data=f,
            file_name=all_zip.name,
            mime="application/zip"
        )

    st.divider()

    if st.button("🔙 Go Back"):
        # Clean up & reset session
        if st.session_state.output_dir and st.session_state.output_dir.exists():
            shutil.rmtree(st.session_state.output_dir.parent, ignore_errors=True)
        st.session_state.clear()
        st.rerun()


