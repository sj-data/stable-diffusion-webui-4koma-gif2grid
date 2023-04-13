# External libraries
import gradio as gr
import numpy as np
from PIL import Image, ImageSequence
from urllib.request import urlopen
from io import BytesIO
import tempfile
import requests
import os

# Internal modules
import modules.scripts as scripts

class Script(scripts.Script):
    def __init__(self):
        self.grid_images = []
        self.selected_images = []
        self.input_images = []
        # Create a temporary directory to store intermediate files
        self.gif2griddir = tempfile.TemporaryDirectory()

    def title(self):
        return "4koma Grid2Gif"

    def clear_grid(self):
        # This method returns an empty list to clear the gallery content
        self.input_images.clear()
        return []

    def send_to_make_grid(self, gallery_images, sd: gr.SelectData):
        selected_index = sd.index
        selected_image_dict = gallery_images[selected_index]
        image_name = selected_image_dict['name']
        img = Image.open(image_name).resize((256, 256))
        # Append the selected image to the list of selected images
        self.selected_images.append(img)
        # Append the selected image to the input_images list
        self.input_images.append(img)
        # Return the entire list of input images
        return self.input_images

    def remove_image_from_grid(self, gallery_images, sd: gr.SelectData):
        selected_index = sd.index
        # Remove the selected image from the input_images list
        self.input_images.pop(selected_index)
        # Return the entire list of input images
        return self.input_images

    def make_grid(self, gallery_images, grid_size):
        # Define a mapping between grid size options and the number of rows and columns
        grid_size_map = {
            "2x2": (2, 2),
            "3x3": (3, 3),
            "4x4": (4, 4)
        }
        rows, cols = grid_size_map[grid_size]

        # Calculate cell_size based on grid size, so the total grid size is always 512x512 pixels
        grid_width = 512
        grid_height = 512
        cell_size = grid_width // cols

        pil_images = []
        for img_dict in gallery_images:
            img_path = img_dict["name"]
            img = Image.open(img_path).resize((cell_size, cell_size))
            pil_images.append(img)

        # Create a blank image with the required grid size
        grid_image = Image.new('RGB', (grid_width, grid_height))

        # Arrange the images in the grid
        for i in range(rows):
            for j in range(cols):
                index = i * cols + j
                if index < len(pil_images):
                    grid_image.paste(pil_images[index], (j * cell_size, i * cell_size))

        # Convert the final image to a numpy array and return it
        return np.array(grid_image)

    def split_gif(self, input_gif_path):
        # Open the local GIF file using its file path
        gif_path = input_gif_path.name

        gif = Image.open(gif_path)

        # Initialize an empty list to store the frame images
        frame_images = []

        # Iterate through the frames of the GIF and append each frame to the list
        for i, frame in enumerate(ImageSequence.Iterator(gif)):
            # Convert each frame to a PIL Image object
            frame_image = frame.copy().convert('RGBA')
            frame_images.append(frame_image)

        # Return the list of PIL Image objects representing the individual frames
        return frame_images

    def split_grid(self, input_img, grid_type):
        img = np.asarray(input_img)
        height, width = img.shape[:2]

        if grid_type == "2x2":
            half_width = width // 2
            half_height = height // 2
            split_images = [
                img[0:half_height, 0:half_width],  # Top-left quadrant
                img[0:half_height, half_width:width],  # Top-right quadrant
                img[half_height:height, 0:half_width],  # Bottom-left quadrant
                img[half_height:height, half_width:width]  # Bottom-right quadrant
            ]

        elif grid_type == "3x3":
            third_width = width // 3
            third_height = height // 3
            split_images = [
                img[0:third_height, 0:third_width],
                img[0:third_height, third_width:2 * third_width],
                img[0:third_height, 2 * third_width:width],
                img[third_height:2 * third_height, 0:third_width],
                img[third_height:2 * third_height, third_width:2 * third_width],
                img[third_height:2 * third_height, 2 * third_width:width],
                img[2 * third_height:height, 0:third_width],
                img[2 * third_height:height, third_width:2 * third_width],
                img[2 * third_height:height, 2 * third_width:width]
            ]

        elif grid_type == "4x4":
            quarter_width = width // 4
            quarter_height = height // 4
            split_images = [
                img[0:quarter_height, 0:quarter_width],
                img[0:quarter_height, quarter_width:2 * quarter_width],
                img[0:quarter_height, 2 * quarter_width:3 * quarter_width],
                img[0:quarter_height, 3 * quarter_width:width],
                img[quarter_height:2 * quarter_height, 0:quarter_width],
                img[quarter_height:2 * quarter_height, quarter_width:2 * quarter_width],
                img[quarter_height:2 * quarter_height, 2 * quarter_width:3 * quarter_width],
                img[quarter_height:2 * quarter_height, 3 * quarter_width:width],
                img[2 * quarter_height:3 * quarter_height, 0:quarter_width],
                img[2 * quarter_height:3 * quarter_height, quarter_width:2 * quarter_width],
                img[2 * quarter_height:3 * quarter_height, 2 * quarter_width:3 * quarter_width],
                img[2 * quarter_height:3 * quarter_height, 3 * quarter_width:width],
                img[3 * quarter_height:height, 0:quarter_width],
                img[3 * quarter_height:height, quarter_width:2 * quarter_width],
                img[3 * quarter_height:height, 2 * quarter_width:3 * quarter_width],
                img[3 * quarter_height:height, 3 * quarter_width:width]
            ]
        else:
            raise ValueError("Invalid grid type. Choose '2x2', '3x3', or '4x4'.")

        return split_images

    def send_to_make_gif(self, gallery_images, name=None):
        # Load images from URLs in the 'data' key of each dictionary
        pil_images = []
        for img_dict in gallery_images:
            response = requests.get(img_dict['data'])
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            pil_images.append(img)

        # Return the loaded PIL images
        return pil_images

    def make_gif(self, input_images, fps, boomerang):
        # Calculate duration for each frame in milliseconds
        duration = int(1000 / fps)

        # Extract the actual images from the dictionaries and load the image data from URLs
        frames = []
        for img_dict in input_images:
            image_url = img_dict['data']
            with urlopen(image_url) as response:
                frames.append(Image.open(response))

        # If boomerang is selected, add frames in reverse order (except the last one)
        if boomerang:
            frames += frames[-2::-1]

        # Create the output GIF file path by joining the temporary directory path with the desired file name
        gif_output_path = os.path.join(self.gif2griddir.name, "output.gif")
        frames[0].save(gif_output_path, save_all=True, append_images=frames[1:], duration=duration, loop=0)

        # Load the created GIF
        return gif_output_path

    def ui(self, is_img2img):
        with gr.Blocks():
            with gr.Tab("Split GIF"):
                # First main row with two columns
                with gr.Row():
                    # Column 1: Input GIF, button to split it, gallery to display frames
                    with gr.Column():
                        gr.Markdown("Step 1: Split the GIF into frames")
                        input_gif = gr.File(label="Select gif image", file_types=['.gif'])
                        split_gif_button = gr.Button(value="Split GIF")
                        frames_gallery_element = gr.Gallery().style(grid=6, height="256px", preview=False)
                        split_gif_button.click(self.split_gif, inputs=[input_gif], outputs=[frames_gallery_element])

                    # Column 2: Dropdown to select grid size, gallery to display selected frames
                    with gr.Column():
                        gr.Markdown("Step 2: Select Grid Size and Frames")
                        grid_size_dropdown = gr.Dropdown(choices=["2x2", "3x3", "4x4"], label="Select grid size",
                                                         value="2x2")
                        input_images_grid = gr.Gallery(label="Select Images for Grid", file_count="multiple",
                                                       interactive=True).style(grid=2, height="256px")
                        # Send selected frames to input_images_grid
                        frames_gallery_element.select(self.send_to_make_grid, inputs=[frames_gallery_element],
                                                      outputs=[input_images_grid])
                        # Connect the remove_image_from_grid function to the select event of the input_images_grid gallery
                        input_images_grid.select(self.remove_image_from_grid, inputs=[input_images_grid],
                                                 outputs=[input_images_grid])
                        clear_grid_button = gr.Button(value="Clear Grid")
                        # Connect the Clear Grid button to the clear_grid method
                        clear_grid_button.click(self.clear_grid, outputs=[input_images_grid])
                # Second main row with a button to create the grid and a display of the finished grid
                with gr.Row():
                    with gr.Column():
                        make_grid_button = gr.Button(value="Make Grid")
                        grid_output = gr.Image(label="Output Grid", height="256px")
                        # Pass input_images_grid and grid_size_dropdown as inputs
                        make_grid_button.click(self.make_grid, inputs=[input_images_grid, grid_size_dropdown],
                                               outputs=[grid_output])

            with gr.Tab("Make GIF"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("Step 5: Split the grid into frames")
                        grid_type = gr.Dropdown(choices=["2x2", "3x3", "4x4"], label="Select grid type", value="2x2")
                        input_image = gr.Image(label="Select grid image")
                        split_button = gr.Button(value="Split grid")
                        # Use gif_gallery_element directly for split output
                        gif_gallery_element = gr.Gallery().style(grid=2, height="auto")
                        split_button.click(self.split_grid, inputs=[input_image, grid_type],
                                           outputs=[gif_gallery_element])
                    with gr.Column():
                        gr.Markdown("Step 6: Make the GIF")
                        fps_slider = gr.Slider(minimum=1, maximum=60, step=1, default=24, label="FPS")
                        boomerang = gr.Checkbox(value=True, label="Boomerang")
                        make_gif_button = gr.Button(label="Make GIF")
                        gif_output = gr.Image(type="filepath", label="Output GIF", interactive=False)
                        make_gif_button.click(self.make_gif, inputs=[gif_gallery_element, fps_slider, boomerang],
                                              outputs=[gif_output])
            return

