import os
import customtkinter as ctk

from tkinter import filedialog, messagebox
from PIL import Image

from converter import convert_multiple_images


# -------------------------------------------------
# APP SETTINGS
# -------------------------------------------------

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ImageConverterApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        # -----------------------------------------
        # WINDOW SETTINGS
        # -----------------------------------------

        self.title("Image Format Converter")

        self.geometry("1000x820")
        self.minsize(900, 750)

        # Selected images
        self.selected_files = []

        # Preview image reference
        self.preview_image = None

        # Default output directory
        self.output_directory = os.path.join(
            os.getcwd(),
            "output"
        )

        os.makedirs(
            self.output_directory,
            exist_ok=True
        )

        self.create_widgets()


    # =================================================
    # CREATE GUI
    # =================================================

    def create_widgets(self):

        # -----------------------------------------
        # TITLE
        # -----------------------------------------

        title_label = ctk.CTkLabel(
            self,
            text="Image Format Converter",
            font=ctk.CTkFont(
                size=30,
                weight="bold"
            )
        )

        title_label.pack(
            pady=(20, 5)
        )

        # -----------------------------------------
        # SUBTITLE
        # -----------------------------------------

        subtitle_label = ctk.CTkLabel(
            self,
            text=(
                "Convert PNG and JPEG images "
                "to TIFF, BMP, PDF and PSD"
            ),
            font=ctk.CTkFont(
                size=14
            )
        )

        subtitle_label.pack(
            pady=(0, 15)
        )

        # -----------------------------------------
        # SCROLLABLE MAIN FRAME
        # -----------------------------------------

        self.main_frame = ctk.CTkScrollableFrame(
            self
        )

        self.main_frame.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 20)
        )

        # -----------------------------------------
        # SELECT IMAGES BUTTON
        # -----------------------------------------

        self.select_button = ctk.CTkButton(
            self.main_frame,
            text="Select Images",
            width=200,
            height=44,
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            ),
            command=self.select_images
        )

        self.select_button.pack(
            pady=(20, 5)
        )

        # -----------------------------------------
        # IMAGE COUNT
        # -----------------------------------------

        self.selected_count_label = ctk.CTkLabel(
            self.main_frame,
            text="No images selected",
            font=ctk.CTkFont(
                size=13
            )
        )

        self.selected_count_label.pack(
            pady=5
        )

        # -----------------------------------------
        # SELECTED FILE LIST
        # -----------------------------------------

        self.file_list_box = ctk.CTkTextbox(
            self.main_frame,
            width=650,
            height=110
        )

        self.file_list_box.pack(
            pady=10
        )

        self.file_list_box.configure(
            state="disabled"
        )

        # -----------------------------------------
        # IMAGE PREVIEW
        # -----------------------------------------

        self.preview_frame = ctk.CTkFrame(
            self.main_frame,
            width=440,
            height=230
        )

        self.preview_frame.pack(
            pady=10
        )

        self.preview_frame.pack_propagate(
            False
        )

        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="First Selected Image Preview",
            font=ctk.CTkFont(
                size=14
            )
        )

        self.preview_label.pack(
            expand=True
        )

        # -----------------------------------------
        # IMAGE INFORMATION
        # -----------------------------------------

        self.info_label = ctk.CTkLabel(
            self.main_frame,
            text="Image information will appear here.",
            justify="left",
            wraplength=820,
            font=ctk.CTkFont(
                size=13
            )
        )

        self.info_label.pack(
            pady=8
        )

        # -----------------------------------------
        # OUTPUT FORMAT LABEL
        # -----------------------------------------

        format_label = ctk.CTkLabel(
            self.main_frame,
            text="Choose Output Format",
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            )
        )

        format_label.pack(
            pady=(12, 5)
        )

        # -----------------------------------------
        # OUTPUT FORMAT DROPDOWN
        # -----------------------------------------

        self.format_dropdown = ctk.CTkOptionMenu(
            self.main_frame,
            values=[
                "TIFF",
                "BMP",
                "PDF",
                "PSD"
            ],
            width=200,
            height=36
        )

        self.format_dropdown.set(
            "TIFF"
        )

        self.format_dropdown.pack(
            pady=5
        )

        # -----------------------------------------
        # OUTPUT FOLDER BUTTON
        # -----------------------------------------

        self.output_button = ctk.CTkButton(
            self.main_frame,
            text="Choose Output Folder",
            width=220,
            height=38,
            command=self.select_output_folder
        )

        self.output_button.pack(
            pady=(12, 5)
        )

        # -----------------------------------------
        # OUTPUT FOLDER LABEL
        # -----------------------------------------

        self.output_label = ctk.CTkLabel(
            self.main_frame,
            text=f"Output: {self.output_directory}",
            wraplength=820,
            font=ctk.CTkFont(
                size=12
            )
        )

        self.output_label.pack(
            pady=5
        )

        # -----------------------------------------
        # ACTION BUTTON FRAME
        # -----------------------------------------

        self.button_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        self.button_frame.pack(
            pady=18
        )

        # -----------------------------------------
        # CONVERT BUTTON
        # -----------------------------------------

        self.convert_button = ctk.CTkButton(
            self.button_frame,
            text="Convert Images",
            width=180,
            height=44,
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            command=self.convert_images
        )

        self.convert_button.grid(
            row=0,
            column=0,
            padx=8,
            pady=5
        )

        # -----------------------------------------
        # RESET BUTTON
        # -----------------------------------------

        self.reset_button = ctk.CTkButton(
            self.button_frame,
            text="Reset",
            width=130,
            height=44,
            command=self.reset_app
        )

        self.reset_button.grid(
            row=0,
            column=1,
            padx=8,
            pady=5
        )

        # -----------------------------------------
        # OPEN FOLDER BUTTON
        # -----------------------------------------

        self.open_folder_button = ctk.CTkButton(
            self.button_frame,
            text="Open Output Folder",
            width=190,
            height=44,
            command=self.open_output_folder
        )

        self.open_folder_button.grid(
            row=0,
            column=2,
            padx=8,
            pady=5
        )

        # -----------------------------------------
        # STATUS
        # -----------------------------------------

        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Ready",
            font=ctk.CTkFont(
                size=13
            )
        )

        self.status_label.pack(
            pady=(0, 20)
        )


    # =================================================
    # SELECT MULTIPLE IMAGES
    # =================================================

    def select_images(self):

        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[
                (
                    "Supported Images",
                    "*.png *.jpg *.jpeg"
                ),
                (
                    "PNG Files",
                    "*.png"
                ),
                (
                    "JPEG Files",
                    "*.jpg *.jpeg"
                )
            ]
        )

        if not files:
            return

        self.selected_files = list(files)

        total_files = len(
            self.selected_files
        )

        self.selected_count_label.configure(
            text=f"{total_files} image(s) selected"
        )

        self.update_file_list()

        # Preview first selected image
        self.show_preview(
            self.selected_files[0]
        )

        # First image information
        self.show_image_information(
            self.selected_files[0]
        )

        self.status_label.configure(
            text="Images loaded successfully."
        )


    # =================================================
    # UPDATE FILE LIST
    # =================================================

    def update_file_list(self):

        self.file_list_box.configure(
            state="normal"
        )

        self.file_list_box.delete(
            "1.0",
            "end"
        )

        for number, file_path in enumerate(
            self.selected_files,
            start=1
        ):

            file_name = os.path.basename(
                file_path
            )

            self.file_list_box.insert(
                "end",
                f"{number}. {file_name}\n"
            )

        self.file_list_box.configure(
            state="disabled"
        )


    # =================================================
    # SHOW IMAGE PREVIEW
    # =================================================

    def show_preview(
        self,
        file_path
    ):

        try:

            with Image.open(
                file_path
            ) as image:

                preview = image.copy()

            preview.thumbnail(
                (410, 210)
            )

            self.preview_image = ctk.CTkImage(
                light_image=preview,
                dark_image=preview,
                size=preview.size
            )

            self.preview_label.configure(
                image=self.preview_image,
                text=""
            )

        except Exception as error:

            self.preview_label.configure(
                image=None,
                text="Preview unavailable"
            )

            messagebox.showerror(
                "Preview Error",
                str(error)
            )


    # =================================================
    # SHOW IMAGE INFORMATION
    # =================================================

    def show_image_information(
        self,
        file_path
    ):

        try:

            with Image.open(
                file_path
            ) as image:

                width, height = image.size
                image_format = image.format
                image_mode = image.mode

            file_size = os.path.getsize(
                file_path
            )

            file_size_kb = (
                file_size / 1024
            )

            info = (
                f"First Image: "
                f"{os.path.basename(file_path)}\n\n"
                f"Format: {image_format}   |   "
                f"Dimensions: {width} × {height} pixels   |   "
                f"Mode: {image_mode}   |   "
                f"File Size: {file_size_kb:.2f} KB"
            )

            self.info_label.configure(
                text=info
            )

        except Exception as error:

            self.info_label.configure(
                text=(
                    "Unable to read image information: "
                    f"{error}"
                )
            )


    # =================================================
    # SELECT OUTPUT FOLDER
    # =================================================

    def select_output_folder(self):

        folder = filedialog.askdirectory(
            title="Choose Output Folder"
        )

        if not folder:
            return

        self.output_directory = folder

        self.output_label.configure(
            text=f"Output: {folder}"
        )

        self.status_label.configure(
            text="Output folder selected."
        )


    # =================================================
    # CONVERT IMAGES
    # =================================================

    def convert_images(self):

        if not self.selected_files:

            messagebox.showwarning(
                "No Images Selected",
                "Please select at least one image."
            )

            return

        output_format = (
            self.format_dropdown.get()
        )

        try:

            self.convert_button.configure(
                state="disabled"
            )

            total_files = len(
                self.selected_files
            )

            self.status_label.configure(
                text=(
                    f"Converting {total_files} image(s) "
                    f"to {output_format}..."
                )
            )

            self.update_idletasks()

            successful_files, failed_files = (
                convert_multiple_images(
                    self.selected_files,
                    self.output_directory,
                    output_format
                )
            )

            success_count = len(
                successful_files
            )

            failed_count = len(
                failed_files
            )

            self.status_label.configure(
                text=(
                    f"Completed: "
                    f"{success_count} successful, "
                    f"{failed_count} failed."
                )
            )

            # -----------------------------------------
            # ALL SUCCESSFUL
            # -----------------------------------------

            if failed_count == 0:

                messagebox.showinfo(
                    "Conversion Complete",
                    (
                        f"{success_count} image(s) "
                        f"successfully converted "
                        f"to {output_format}.\n\n"
                        f"Output Folder:\n"
                        f"{self.output_directory}"
                    )
                )

            # -----------------------------------------
            # SOME FAILED
            # -----------------------------------------

            else:

                error_text = ""

                for failed in failed_files:

                    file_name = os.path.basename(
                        failed["file"]
                    )

                    error_text += (
                        f"\n{file_name}: "
                        f"{failed['error']}"
                    )

                messagebox.showwarning(
                    "Conversion Completed",
                    (
                        f"Successful: {success_count}\n"
                        f"Failed: {failed_count}\n"
                        f"{error_text}"
                    )
                )

        except Exception as error:

            self.status_label.configure(
                text="Conversion failed."
            )

            messagebox.showerror(
                "Conversion Error",
                str(error)
            )

        finally:

            self.convert_button.configure(
                state="normal"
            )


    # =================================================
    # OPEN OUTPUT FOLDER
    # =================================================

    def open_output_folder(self):

        if not os.path.exists(
            self.output_directory
        ):

            messagebox.showwarning(
                "Folder Not Found",
                "Output folder does not exist."
            )

            return

        try:

            os.startfile(
                self.output_directory
            )

        except Exception as error:

            messagebox.showerror(
                "Error",
                (
                    "Unable to open output folder.\n\n"
                    f"{error}"
                )
            )


    # =================================================
    # RESET APP
    # =================================================

    def reset_app(self):

        # Remove selected files
        self.selected_files = []

        # Remove image reference
        self.preview_image = None

        # Reset image count
        self.selected_count_label.configure(
            text="No images selected"
        )

        # Clear file list
        self.file_list_box.configure(
            state="normal"
        )

        self.file_list_box.delete(
            "1.0",
            "end"
        )

        self.file_list_box.configure(
            state="disabled"
        )

        # Reset preview
        self.preview_label.configure(
            image=None,
            text="First Selected Image Preview"
        )

        # Reset information
        self.info_label.configure(
            text="Image information will appear here."
        )

        # Reset output format
        self.format_dropdown.set(
            "TIFF"
        )

        # Reset status
        self.status_label.configure(
            text="Ready"
        )


# =====================================================
# RUN APPLICATION
# =====================================================

if __name__ == "__main__":

    app = ImageConverterApp()

    app.mainloop()