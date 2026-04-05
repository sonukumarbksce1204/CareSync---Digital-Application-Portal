from whitenoise.storage import CompressedManifestStaticFilesStorage

class CustomWhiteNoiseStorage(CompressedManifestStaticFilesStorage):
    """
    Custom WhiteNoise storage that disables strict manifest checking.
    This prevents collectstatic from crashing when 3rd party apps (like django.contrib.admin)
    have CSS files that reference missing images or assets.
    """
    manifest_strict = False
