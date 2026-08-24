import base64
import ctypes

from dataclasses import (
    dataclass,
)

from io import (
    BytesIO,
)

from PIL import (
    Image,
    ImageGrab,
)


@dataclass(
    frozen=True
)
class ScreenCapture:
    image_data: str

    # Size of the captured screen/region before resizing.
    original_width: int
    original_height: int

    # Size actually sent to the vision model.
    transmitted_width: int
    transmitted_height: int

    # Absolute virtual-desktop coordinates of the
    # captured region's top-left corner.
    origin_x: int
    origin_y: int

    # Name of captured region.
    region_name: str = "full"


class ScreenCaptureService:
    MAX_IMAGE_DIMENSION = 1600
    FOCUSED_IMAGE_DIMENSION = 1600

    # Windows virtual-screen metrics.
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77

    # ==================================================
    # CAPTURE FULL SCREEN
    # ==================================================

    def capture(
        self,
    ) -> ScreenCapture:
        image = (
            ImageGrab.grab(
                all_screens=True,
            )
        )

        origin_x, origin_y = (
            self._get_virtual_screen_origin()
        )

        return (
            self._build_capture(
                image=image,
                origin_x=origin_x,
                origin_y=origin_y,
                region_name="full",
                allow_upscale=False,
            )
        )

    # ==================================================
    # CAPTURE FOCUSED REGION
    # ==================================================

    def capture_region(
        self,
        region_name: str,
    ) -> ScreenCapture:
        normalized_region = (
            region_name
            .strip()
            .lower()
            .replace(
                "-",
                "_",
            )
        )

        image = (
            ImageGrab.grab(
                all_screens=True,
            )
        )

        width, height = (
            image.size
        )

        left, top, right, bottom = (
            self._get_region_box(
                region_name=(
                    normalized_region
                ),
                width=width,
                height=height,
            )
        )

        cropped = (
            image.crop(
                (
                    left,
                    top,
                    right,
                    bottom,
                )
            )
        )

        virtual_origin_x, virtual_origin_y = (
            self._get_virtual_screen_origin()
        )

        absolute_origin_x = (
            virtual_origin_x
            + left
        )

        absolute_origin_y = (
            virtual_origin_y
            + top
        )

        return (
            self._build_capture(
                image=cropped,
                origin_x=(
                    absolute_origin_x
                ),
                origin_y=(
                    absolute_origin_y
                ),
                region_name=(
                    normalized_region
                ),
                allow_upscale=True,
            )
        )

    # ==================================================
    # BUILD CAPTURE
    # ==================================================

    def _build_capture(
        self,
        image: Image.Image,
        origin_x: int,
        origin_y: int,
        region_name: str,
        allow_upscale: bool,
    ) -> ScreenCapture:
        original_width, original_height = (
            image.size
        )

        prepared = (
            self._resize_image(
                image=image,
                allow_upscale=(
                    allow_upscale
                ),
            )
        )

        transmitted_width, transmitted_height = (
            prepared.size
        )

        if (
            prepared.mode
            != "RGB"
        ):
            prepared = (
                prepared.convert(
                    "RGB"
                )
            )

        buffer = (
            BytesIO()
        )

        prepared.save(
            buffer,
            format="JPEG",
            quality=88,
            optimize=True,
        )

        image_data = (
            base64
            .b64encode(
                buffer.getvalue()
            )
            .decode(
                "ascii"
            )
        )

        return ScreenCapture(
            image_data=image_data,
            original_width=(
                original_width
            ),
            original_height=(
                original_height
            ),
            transmitted_width=(
                transmitted_width
            ),
            transmitted_height=(
                transmitted_height
            ),
            origin_x=(
                origin_x
            ),
            origin_y=(
                origin_y
            ),
            region_name=(
                region_name
            ),
        )

    # ==================================================
    # NORMALIZED → REAL SCREEN COORDINATES
    # ==================================================

    def normalized_to_screen(
        self,
        capture: ScreenCapture,
        x: int,
        y: int,
    ) -> tuple[
        int,
        int,
    ]:
        if not (
            0 <= x <= 1000
            and
            0 <= y <= 1000
        ):
            raise ValueError(
                "Normalized coordinates must "
                "be between 0 and 1000."
            )

        relative_x = round(
            (
                x / 1000
            )
            * max(
                capture.original_width - 1,
                0,
            )
        )

        relative_y = round(
            (
                y / 1000
            )
            * max(
                capture.original_height - 1,
                0,
            )
        )

        return (
            capture.origin_x
            + relative_x,

            capture.origin_y
            + relative_y,
        )

    # ==================================================
    # TRANSMITTED IMAGE → REAL SCREEN COORDINATES
    # ==================================================

    def transmitted_to_screen(
        self,
        capture: ScreenCapture,
        x: int,
        y: int,
    ) -> tuple[
        int,
        int,
    ]:
        if (
            capture.transmitted_width
            <= 1
            or
            capture.transmitted_height
            <= 1
        ):
            raise ValueError(
                "Transmitted image dimensions "
                "are invalid."
            )

        if not (
            0
            <= x
            < capture.transmitted_width
        ):
            raise ValueError(
                "X coordinate is outside "
                "the transmitted image."
            )

        if not (
            0
            <= y
            < capture.transmitted_height
        ):
            raise ValueError(
                "Y coordinate is outside "
                "the transmitted image."
            )

        relative_x = round(
            (
                x
                / (
                    capture
                    .transmitted_width
                    - 1
                )
            )
            * max(
                capture.original_width
                - 1,
                0,
            )
        )

        relative_y = round(
            (
                y
                / (
                    capture
                    .transmitted_height
                    - 1
                )
            )
            * max(
                capture.original_height
                - 1,
                0,
            )
        )

        screen_x = (
            capture.origin_x
            + relative_x
        )

        screen_y = (
            capture.origin_y
            + relative_y
        )

        return (
            screen_x,
            screen_y,
        )

    # ==================================================
    # REGION DEFINITIONS
    # ==================================================

    def _get_region_box(
        self,
        region_name: str,
        width: int,
        height: int,
    ) -> tuple[
        int,
        int,
        int,
        int,
    ]:
        if (
            width <= 0
            or
            height <= 0
        ):
            raise ValueError(
                "Screen dimensions are invalid."
            )

        regions: dict[
            str,
            tuple[
                float,
                float,
                float,
                float,
            ],
        ] = {
            "top_left": (
                0.00,
                0.00,
                0.50,
                0.50,
            ),

            "top_right": (
                0.50,
                0.00,
                1.00,
                0.50,
            ),

            "bottom_left": (
                0.00,
                0.50,
                0.50,
                1.00,
            ),

            "bottom_right": (
                0.50,
                0.50,
                1.00,
                1.00,
            ),

            "top": (
                0.00,
                0.00,
                1.00,
                0.42,
            ),

            "bottom": (
                0.00,
                0.58,
                1.00,
                1.00,
            ),

            "left": (
                0.00,
                0.00,
                0.50,
                1.00,
            ),

            "right": (
                0.50,
                0.00,
                1.00,
                1.00,
            ),

            "center": (
                0.18,
                0.15,
                0.82,
                0.85,
            ),
        }

        fractions = (
            regions.get(
                region_name
            )
        )

        if (
            fractions
            is None
        ):
            raise ValueError(
                (
                    "Unsupported screen region: "
                    f"{region_name}"
                )
            )

        (
            left_fraction,
            top_fraction,
            right_fraction,
            bottom_fraction,
        ) = fractions

        left = round(
            width
            * left_fraction
        )

        top = round(
            height
            * top_fraction
        )

        right = round(
            width
            * right_fraction
        )

        bottom = round(
            height
            * bottom_fraction
        )

        left = max(
            0,
            min(
                left,
                width - 1,
            ),
        )

        top = max(
            0,
            min(
                top,
                height - 1,
            ),
        )

        right = max(
            left + 1,
            min(
                right,
                width,
            ),
        )

        bottom = max(
            top + 1,
            min(
                bottom,
                height,
            ),
        )

        return (
            left,
            top,
            right,
            bottom,
        )

    # ==================================================
    # RESIZE IMAGE
    # ==================================================

    def _resize_image(
        self,
        image: Image.Image,
        allow_upscale: bool,
    ) -> Image.Image:
        width, height = (
            image.size
        )

        largest = max(
            width,
            height,
        )

        if (
            largest <= 0
        ):
            raise ValueError(
                "Image dimensions are invalid."
            )

        target_dimension = (
            self.FOCUSED_IMAGE_DIMENSION
            if allow_upscale
            else self.MAX_IMAGE_DIMENSION
        )

        # Full-screen capture should never upscale.
        if (
            not allow_upscale
            and largest
            <= target_dimension
        ):
            return image

        if (
            allow_upscale
            and largest
            == target_dimension
        ):
            return image

        scale = (
            target_dimension
            / largest
        )

        if (
            not allow_upscale
            and scale >= 1.0
        ):
            return image

        new_width = max(
            1,
            round(
                width
                * scale
            ),
        )

        new_height = max(
            1,
            round(
                height
                * scale
            ),
        )

        return (
            image.resize(
                (
                    new_width,
                    new_height,
                ),
                Image.Resampling.LANCZOS,
            )
        )

    # ==================================================
    # WINDOWS VIRTUAL SCREEN ORIGIN
    # ==================================================

    def _get_virtual_screen_origin(
        self,
    ) -> tuple[
        int,
        int,
    ]:
        try:
            user32 = (
                ctypes
                .windll
                .user32
            )

            origin_x = (
                user32
                .GetSystemMetrics(
                    self.SM_XVIRTUALSCREEN
                )
            )

            origin_y = (
                user32
                .GetSystemMetrics(
                    self.SM_YVIRTUALSCREEN
                )
            )

            return (
                int(
                    origin_x
                ),
                int(
                    origin_y
                ),
            )

        except (
            AttributeError,
            OSError,
        ):
            return (
                0,
                0,
            )


screen_capture_service = (
    ScreenCaptureService()
)