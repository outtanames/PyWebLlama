import io
import time
from datetime import datetime
import os
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from playwright.sync_api import Page, sync_playwright


class Agent:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def goto(self, url, session_id):
        print("Going to url")
        self.session_id = session_id
        self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        self.collect_data()

    def take_screenshot(self):
        screenshot_bytes = self.page.screenshot(full_page=False)
        screenshot_image = Image.open(io.BytesIO(screenshot_bytes))
        return screenshot_image

    def get_clickable_elements_metadata(self):
        return self.page.evaluate(
            # """
            # () => {
            #     const clickableSelectors = [
            #     'button',
            #     'a',
            #     'input[type="button"]',
            #     'input[type="submit"]',
            #     'input[type="reset"]',
            #     'input[type="image"]',
            #     'input[type="file"]',
            #     'input[type="text"]',
            #     '[onclick]',
            #     '[role="button"]',
            #     '[role="link"]',
            #     '[tabindex]',
            #     'select',
            #     'textarea'
            # ];
            # const elements = document.querySelectorAll(clickableSelectors.join(','));
            # return Array.from(elements).map(el => {
            #     const rect = el.getBoundingClientRect();
            #     return {
            #         tag: el.tagName.toLowerCase(),
            #         outerHTML: el.outerHTML,
            #         boundingBox: {
            #             x: rect.left,
            #             y: rect.top,
            #             width: rect.width,
            #             height: rect.height
            #         }
            #     };
            # });
            # }
            # """
            """
            () => {
    const clickableSelectors = [
        'button',
        'a',
        'input[type="button"]',
        'input[type="submit"]',
        'input[type="reset"]',
        'input[type="image"]',
        'input[type="file"]',
        'input[type="text"]',
        '[onclick]',
        '[role="button"]',
        '[role="link"]',
        '[tabindex]',
        'select',
        'textarea',
        'label',
        'div[tabindex]',
        'span[tabindex]'
    ];

    // To capture elements with event listeners
    function hasEventListener(el, event) {
        const clone = el.cloneNode();
        const result = clone.addEventListener(event, () => {});
        return !result;
    }

    const elements = document.querySelectorAll(clickableSelectors.join(','));

    return Array.from(elements).map(el => {
        const rect = el.getBoundingClientRect();
        return {
            tag: el.tagName.toLowerCase(),
            outerHTML: el.outerHTML,
            boundingBox: {
                x: rect.left,
                y: rect.top,
                width: rect.width,
                height: rect.height
            }
        };
    }).filter(el => el.boundingBox.width > 0 && el.boundingBox.height > 0); // Ensure only visible elements are included
}

"""
        )

    def collect_data(self):
        while True:
            image = self.take_screenshot()
            clickable_elements = self.get_clickable_elements_metadata()
            # Draw all clickable elements on the image, using a range of colors
            # for the bounding boxes
            dt_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path = os.getenv("SC_PATH")
            draw_bounding_boxes(
                clickable_elements, image, f"{path}/sc_{self.session_id}_{dt_str}.png"
            )

            print(f"Collected data: {len(clickable_elements)} bounding boxes")
            time.sleep(5)


def draw_bounding_boxes(elements, image, image_path):
    # Create an image with a higher resolution
    scale_factor = 2
    width = image.width * scale_factor
    height = image.height * scale_factor
    scaled_image = image.resize((width, height))
    draw = ImageDraw.Draw(scaled_image)
    idx = 0
    for element in elements:
        bbox = element["boundingBox"]
        bbox = {k: v * scale_factor for k, v in bbox.items()}
        """
        draw.rectangle(
            [bbox["x"], bbox["y"], bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]],
            outline="red",
            width=2,
        )
        """

        font = ImageFont.truetype(
            font="/System/Library/Fonts/Times.ttc", size=32
        )  # Set the font size to 24

        # draw in the middle of the bounding box
        draw.text(
            (bbox["x"] + bbox["width"] // 2, bbox["y"] + bbox["height"] // 2),
            str(idx),
            fill="black",
            font=font,
        )

        # draw the idx to the right of the bounding box
        """
        draw.text((bbox["x"] + bbox["width"] + 5, bbox["y"] + bbox["height"] // 2), str(idx), fill="black", font=font)
        """
        idx += 1
    scaled_image.save(image_path)  # Save the image with bounding boxes


if __name__ == "__main__":
    agent = Agent()
    # agent.goto("https://sfbay.craigslist.org/")
    # agent.goto("https://sfbay.craigslist.org/search/gra#search=1~gallery~0~0")
    agent.goto("https://www.zillow.com/homes/San-Francisco,-CA_rb/")
