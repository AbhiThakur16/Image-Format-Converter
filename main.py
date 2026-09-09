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

        self.title("Image Format Converter")
        self.geometry("1000x850")
        self.minsize(900, 750)

        self.selected_files = []
        self.preview_image = None

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

        subtitle_label = ctk.CTkLabel(
            self,
            text=(
                "Convert PNG/JPEG images to "
                "TIFF, BMP, PDF and PSD"
            ),
            font=ctk.CTkFont(size=14)
        )

        subtitle_label.pack(
            pady=(0, 15)
        )

        # -----------------------------------------
        # MAIN SCROLLABLE FRAME
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
        # SELECT IMAGES
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

        self.selected_count_label = ctk.CTkLabel(
            self.main_frame,
            text="No images selected"
        )

        self.selected_count_label.pack(
            pady=5
        )

        # -----------------------------------------
        # FILE LIST
        # -----------------------------------------

        self.file_list_box = ctk.CTkTextbox(
            self.main_frame,
            width=650,
            height=100
        )

        self.file_list_box.pack(
            pady=8
        )

        self.file_list_box.configure(
            state="disabled"
        )

        # -----------------------------------------
        # PREVIEW
        # -----------------------------------------

        self.preview_frame = ctk.CTkFrame(
            self.main_frame,
            width=440,
            height=220
        )

        self.preview_frame.pack(
            pady=10
        )

        self.preview_frame.pack_propagate(
            False
        )

        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="First Selected Image Preview"
        )

        self.preview_label.pack(
            expand=True
        )

        # -----------------------------------------
        # IMAGE INFO
        # -----------------------------------------

        self.info_label = ctk.CTkLabel(
            self.main_frame,
            text="Image information will appear here.",
            wraplength=820
        )

        self.info_label.pack(
            pady=8
        )

        # -----------------------------------------
        # OUTPUT FORMAT
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

        self.format_dropdown = ctk.CTkOptionMenu(
            self.main_frame,
            values=[
                "TIFF",
                "BMP",
                "PDF",
                "PSD"
            ],
            width=200,
            command=self.on_format_change
        )

        self.format_dropdown.set(
            "TIFF"
        )

        self.format_dropdown.pack(
            pady=5
        )

        # =========================================
        # TIFF / BMP SETTINGS FRAME
        # =========================================

        self.resize_settings_frame = ctk.CTkFrame(
            self.main_frame
        )

        self.resize_settings_frame.pack(
            padx=20,
            pady=15
        )

        settings_title = ctk.CTkLabel(
            self.resize_settings_frame,
            text="Pixel Size & DPI Settings",
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            )
        )

        settings_title.grid(
            row=0,
            column=0,
            columnspan=4,
            padx=10,
            pady=(12, 10)
        )

        # -----------------------------------------
        # WIDTH
        # -----------------------------------------

        width_label = ctk.CTkLabel(
            self.resize_settings_frame,
            text="Width (px)"
        )

        width_label.grid(
            row=1,
            column=0,
            padx=10,
            pady=8
        )

        self.width_entry = ctk.CTkEntry(
            self.resize_settings_frame,
            width=130,
            placeholder_text="e.g. 1920"
        )

        self.width_entry.grid(
            row=1,
            column=1,
            padx=10,
            pady=8
        )

        # -----------------------------------------
        # HEIGHT
        # -----------------------------------------

        height_label = ctk.CTkLabel(
            self.resize_settings_frame,
            text="Height (px)"
        )

        height_label.grid(
            row=1,
            column=2,
            padx=10,
            pady=8
        )

        self.height_entry = ctk.CTkEntry(
            self.resize_settings_frame,
            width=130,
            placeholder_text="e.g. 1080"
        )

        self.height_entry.grid(
            row=1,
            column=3,
            padx=10,
            pady=8
        )

        # -----------------------------------------
        # DPI
        # -----------------------------------------

        dpi_label = ctk.CTkLabel(
            self.resize_settings_frame,
            text="DPI"
        )

        dpi_label.grid(
            row=2,
            column=0,
            padx=10,
            pady=8
        )

        self.dpi_dropdown = ctk.CTkOptionMenu(
            self.resize_settings_frame,
            values=[
                "72",
                "96",
                "150",
                "300",
                "Custom"
            ],
            width=130,
            command=self.on_dpi_change
        )

        self.dpi_dropdown.set(
            "300"
        )

        self.dpi_dropdown.grid(
            row=2,
            column=1,
            padx=10,
            pady=8
        )

        # -----------------------------------------
        # CUSTOM DPI
        # -----------------------------------------

        self.custom_dpi_label = ctk.CTkLabel(
            self.resize_settings_frame,
            text="Custom DPI"
        )

        self.custom_dpi_entry = ctk.CTkEntry(
            self.resize_settings_frame,
            width=130,
            placeholder_text="e.g. 600"
        )

        # Hide custom DPI initially
        self.custom_dpi_label.grid_remove()
        self.custom_dpi_entry.grid_remove()

        # -----------------------------------------
        # HELP TEXT
        # -----------------------------------------

        self.settings_help = ctk.CTkLabel(
            self.resize_settings_frame,
            text=(
                "Leave Width and Height empty to keep "
                "the original pixel size."
            ),
            font=ctk.CTkFont(size=12)
        )

        self.settings_help.grid(
            row=3,
            column=0,
            columnspan=4,
            padx=10,
            pady=(5, 12)
        )

        # -----------------------------------------
        # OUTPUT FOLDER
        # -----------------------------------------

        self.output_button = ctk.CTkButton(
            self.main_frame,
            text="Choose Output Folder",
            width=220,
            height=38,
            command=self.select_output_folder
        )

        self.output_button.pack(
            pady=(10, 5)
        )

        self.output_label = ctk.CTkLabel(
            self.main_frame,
            text=f"Output: {self.output_directory}",
            wraplength=820
        )

        self.output_label.pack(
            pady=5
        )

        # -----------------------------------------
        # ACTION BUTTONS
        # -----------------------------------------

        self.button_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        self.button_frame.pack(
            pady=18
        )

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
            padx=8
        )

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
            padx=8
        )

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
            padx=8
        )

        # -----------------------------------------
        # STATUS
        # -----------------------------------------

        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Ready"
        )

        self.status_label.pack(
            pady=(0, 20)
        )


    # =================================================
    # FORMAT CHANGE
    # =================================================

    def on_format_change(self, selected_format):

        if selected_format in (
            "TIFF",
            "BMP"
        ):
            self.resize_settings_frame.pack(
                padx=20,
                pady=15
            )

        else:
            self.resize_settings_frame.pack_forget()


    # =================================================
    # DPI CHANGE
    # =================================================

    def on_dpi_change(self, selected_dpi):

        if selected_dpi == "Custom":

            self.custom_dpi_label.grid(
                row=2,
                column=2,
                padx=10,
                pady=8
            )

            self.custom_dpi_entry.grid(
                row=2,
                column=3,
                padx=10,
                pady=8
            )

        else:

            self.custom_dpi_label.grid_remove()
            self.custom_dpi_entry.grid_remove()


    # =================================================
    # SELECT IMAGES
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

        self.selected_files = list(
            files
        )

        total_files = len(
            self.selected_files
        )

        self.selected_count_label.configure(
            text=f"{total_files} image(s) selected"
        )

        self.update_file_list()

        self.show_preview(
            self.selected_files[0]
        )

        self.show_image_information(
            self.selected_files[0]
        )

        self.fill_original_dimensions(
            self.selected_files[0]
        )

        self.status_label.configure(
            text="Images loaded successfully."
        )


    # =================================================
    # ORIGINAL DIMENSIONS
    # =================================================

    def fill_original_dimensions(
        self,
        file_path
    ):

        try:

            with Image.open(
                file_path
            ) as image:

                width, height = image.size

            self.width_entry.delete(
                0,
                "end"
            )

            self.width_entry.insert(
                0,
                str(width)
            )

            self.height_entry.delete(
                0,
                "end"
            )

            self.height_entry.insert(
                0,
                str(height)
            )

        except Exception:
            pass


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
    # PREVIEW
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
                (410, 200)
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
    # IMAGE INFORMATION
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

                dpi = image.info.get(
                    "dpi",
                    "Not available"
                )

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
                f"Dimensions: {width} × {height}px   |   "
                f"Mode: {image_mode}   |   "
                f"Original DPI: {dpi}   |   "
                f"Size: {file_size_kb:.2f} KB"
            )

            self.info_label.configure(
                text=info
            )

        except Exception as error:

            self.info_label.configure(
                text=f"Unable to read image: {error}"
            )


    # =================================================
    # OUTPUT FOLDER
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
    # GET RESIZE SETTINGS
    # =================================================

    def get_resize_settings(self):

        output_format = (
            self.format_dropdown.get()
        )

        if output_format not in (
            "TIFF",
            "BMP"
        ):
            return None, None, None

        width_text = (
            self.width_entry.get().strip()
        )

        height_text = (
            self.height_entry.get().strip()
        )

        # Keep original size if both blank
        if (
            width_text == ""
            and height_text == ""
        ):
            width = None
            height = None

        else:

            if (
                width_text == ""
                or height_text == ""
            ):
                raise ValueError(
                    "Please enter both Width and Height."
                )

            width = int(
                width_text
            )

            height = int(
                height_text
            )

            if width <= 0 or height <= 0:
                raise ValueError(
                    "Width and Height must be greater than 0."
                )

        selected_dpi = (
            self.dpi_dropdown.get()
        )

        if selected_dpi == "Custom":

            custom_dpi = (
                self.custom_dpi_entry.get().strip()
            )

            if not custom_dpi:
                raise ValueError(
                    "Please enter a custom DPI."
                )

            dpi = int(
                custom_dpi
            )

        else:
            dpi = int(
                selected_dpi
            )

        if dpi <= 0:
            raise ValueError(
                "DPI must be greater than 0."
            )

        return width, height, dpi


    # =================================================
    # CONVERT
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

            width, height, dpi = (
                self.get_resize_settings()
            )

            self.convert_button.configure(
                state="disabled"
            )

            self.status_label.configure(
                text="Converting images..."
            )

            self.update_idletasks()

            successful_files, failed_files = (
                convert_multiple_images(
                    self.selected_files,
                    self.output_directory,
                    output_format,
                    width,
                    height,
                    dpi
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

            if failed_count == 0:

                details = (
                    f"{success_count} image(s) "
                    f"converted to {output_format}."
                )

                if output_format in (
                    "TIFF",
                    "BMP"
                ):

                    if width and height:

                        details += (
                            f"\n\nPixel Size: "
                            f"{width} × {height}px"
                        )

                    details += (
                        f"\nDPI: {dpi}"
                    )

                details += (
                    f"\n\nSaved at:\n"
                    f"{self.output_directory}"
                )

                messagebox.showinfo(
                    "Conversion Complete",
                    details
                )

            else:

                error_text = ""

                for failed in failed_files:

                    error_text += (
                        f"\n"
                        f"{os.path.basename(failed['file'])}: "
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

        except ValueError as error:

            messagebox.showwarning(
                "Invalid Settings",
                str(error)
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

        try:

            os.startfile(
                self.output_directory
            )

        except Exception as error:

            messagebox.showerror(
                "Error",
                str(error)
            )


    # =================================================
    # RESET
    # =================================================

    def reset_app(self):

        self.selected_files = []
        self.preview_image = None

        self.selected_count_label.configure(
            text="No images selected"
        )

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

        self.preview_label.configure(
            image=None,
            text="First Selected Image Preview"
        )

        self.info_label.configure(
            text="Image information will appear here."
        )

        self.width_entry.delete(
            0,
            "end"
        )

        self.height_entry.delete(
            0,
            "end"
        )

        self.custom_dpi_entry.delete(
            0,
            "end"
        )

        self.format_dropdown.set(
            "TIFF"
        )

        self.dpi_dropdown.set(
            "300"
        )

        self.on_format_change(
            "TIFF"
        )

        self.on_dpi_change(
            "300"
        )

        self.status_label.configure(
            text="Ready"
        )


# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":

    app = ImageConverterApp()

    app.mainloop()