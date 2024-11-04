import tkinter as tk
from tkinter import filedialog, Label, Button, messagebox, Checkbutton, IntVar
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import pytesseract
from deep_translator import GoogleTranslator
from langdetect import detect
import numpy as np
from fpdf import FPDF  # For PDF creation
from docx import Document  # For Word document creation
import os

# Pre-processing functions
def detect_noise(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray_image, cv2.CV_64F).var()
    return laplacian_var < 100

def adjust_contrast(image):
    return cv2.equalizeHist(image)

def sharpen_image(image):
    kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
    return cv2.filter2D(image, -1, kernel)

def deskew(image):
    coords = np.column_stack(np.where(image > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def preprocess_image(image_path):
    image = cv2.imread(image_path)
    if detect_noise(image):
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised_image = cv2.fastNlMeansDenoising(gray_image, None, 30, 7, 21)
        sharpened_image = sharpen_image(denoised_image)
        contrast_adjusted_image = adjust_contrast(sharpened_image)
        deskewed_image = deskew(contrast_adjusted_image)
        processed_image = deskewed_image
    else:
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processed_image = cv2.GaussianBlur(gray_image, (3, 3), 0)
    
    thresh_image = cv2.adaptiveThreshold(
        processed_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh_image

# OCR function
def perform_ocr(image):
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(image, lang='eng+fra+spa+deu', config=custom_config)
    with open('ocr_output.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    return text

# Translation function
def translate_text():
    with open('ocr_output.txt', 'r', encoding='utf-8') as file:
        text = file.read()
    
    language = detect(text)
    translator = GoogleTranslator(source=language, target='en')
    
    if language != 'en':
        chunks = split_text(text, max_length=5000)
        translated_text = ''
        for chunk in chunks:
            translated_text += translator.translate(chunk) + ' '
    else:
        translated_text = text
    
    with open('translated_output.txt', 'w', encoding='utf-8') as f:
        f.write(translated_text)
    
    return translated_text, language

# Helper function to split text into chunks
def split_text(text, max_length=5000):
    chunks = []
    while len(text) > max_length:
        split_index = text[:max_length].rfind(' ')
        if split_index == -1:
            split_index = max_length
        chunks.append(text[:split_index])
        text = text[split_index:]
    chunks.append(text)
    return chunks

# Save translated output as PDF
def save_as_pdf():
    translated_text, _ = translate_text()
    
    # Determine the next available filename
    base_filename = "translated_output"
    file_counter = 1
    pdf_filename = f"{base_filename}{file_counter}.pdf"
    
    # Check if the file already exists and increment the counter if it does
    while os.path.exists(pdf_filename):
        file_counter += 1
        pdf_filename = f"{base_filename}{file_counter}.pdf"
    
    # Create and save the PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, translated_text)
    pdf.output(pdf_filename)
    messagebox.showinfo("Success", f"Saved as {pdf_filename}")


# Save translated output as Word document
def save_as_word():
    translated_text, _ = translate_text()
    doc = Document()
    doc.add_paragraph(translated_text)
    doc.save("translated_output.docx")
    messagebox.showinfo("Success", "Saved as Word Document")

# Tkinter GUI
def open_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp *.pdf")])
    if file_path:
        load_image(file_path)

def load_image(file_path):
    global img, processed_image
    img = Image.open(file_path)
    img.thumbnail((400, 400))
    img_tk = ImageTk.PhotoImage(img)
    image_label.config(image=img_tk)
    image_label.image = img_tk
    ocr_button.config(state=tk.NORMAL)
    processed_image = preprocess_image(file_path)

# Language mapping dictionary
language_names = {
    'en': 'English',
    'fr': 'French',
    'es': 'Spanish',
    'de': 'German',
    'ca': 'Catalan',
    'it': 'Italian',
    'pt': 'Portuguese',
}

def perform_ocr_and_translate():
    ocr_text = perform_ocr(processed_image)
    translated_text, detected_language = translate_text()
    
    # Get full language name from the mapping
    full_language_name = language_names.get(detected_language, detected_language).capitalize()

    # Display detected language
    language_label.config(text=f"Detected Language: {full_language_name.capitalize()}")

    with open('ocr_output.txt', 'r') as f:
        ocr_output = f.read()
    with open('translated_output.txt', 'r') as f:
        translated_output = f.read()
    
    ocr_output_window = tk.Toplevel(root)
    ocr_output_window.title("OCR Output")
    ocr_label = tk.Label(ocr_output_window, text="OCR Output", font=("Arial", 14))
    ocr_label.pack(pady=10)
    ocr_textbox = tk.Text(ocr_output_window, wrap="word")
    ocr_textbox.insert("1.0", ocr_output)
    ocr_textbox.pack(padx=10, pady=10)

    translated_output_window = tk.Toplevel(root)
    translated_output_window.title("Translated Output")
    translated_label = tk.Label(translated_output_window, text="Translated Output", font=("Arial", 14))
    translated_label.pack(pady=10)
    translated_textbox = tk.Text(translated_output_window, wrap="word")
    translated_textbox.insert("1.0", translated_output)
    translated_textbox.pack(padx=10, pady=10)

# Dark mode switch
def toggle_dark_mode():
    if dark_mode_var.get():
        root.config(bg='black')
        title_label.config(bg='black', fg='white')
        language_label.config(bg='black', fg='white')
        dark_mode_button.config(bg='black', fg='white')
        load_button.config(bg='black', fg='white')
        ocr_button.config(bg='black', fg='white')
        pdf_button.config(bg='black', fg='white')
        word_button.config(bg='black', fg='white')
    else:
        root.config(bg='white')
        title_label.config(bg='white', fg='black')
        language_label.config(bg='white', fg='black')
        dark_mode_button.config(bg='white', fg='black')
        load_button.config(bg='white', fg='black')
        ocr_button.config(bg='white', fg='black')
        pdf_button.config(bg='white', fg='black')
        word_button.config(bg='white', fg='black')

# Initialize Tkinter
root = tk.Tk()
root.title("OCR System")
root.geometry("500x700")

# Dark mode variable
dark_mode_var = IntVar()

# Title Label
title_label = Label(root, text="OCR System", font=("Helvetica", 20))
title_label.pack(pady=20)

# Image Label (Displays loaded image)
image_label = Label(root)
image_label.pack(pady=10)

# Load Image Button
load_button = Button(root, text="Upload Image", command=open_file, width=15)
load_button.pack(pady=10)

# Detected Language Label
language_label = Label(root, text="Detected Language: None", font=("Helvetica", 12))
language_label.pack(pady=10)

# OCR and Translation Button
ocr_button = Button(root, text="Perform OCR & Translate", command=perform_ocr_and_translate, state=tk.DISABLED, width=20)
ocr_button.pack(pady=10)

# Save as PDF Button
pdf_button = Button(root, text="Save as PDF", command=save_as_pdf, width=15)
pdf_button.pack(pady=10)

# Save as Word Button
word_button = Button(root, text="Save as Word", command=save_as_word, width=15)
word_button.pack(pady=10)

# Dark Mode Toggle
dark_mode_button = Checkbutton(root, text="Dark Mode", variable=dark_mode_var, command=toggle_dark_mode)
dark_mode_button.pack(pady=10)

# Start Tkinter
root.mainloop()
