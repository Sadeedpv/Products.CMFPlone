from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.fti import DexterityFTI
from plone.dexterity.utils import iterSchemata
from plone.namedfile.field import NamedBlobImage
from plone.namedfile.file import NamedImage
from plone.supermodel import model
from Products.CMFPlone.image_scales.interfaces import IImageScalesAdapter
from Products.CMFPlone.image_scales.interfaces import IImageScalesFieldAdapter
from Products.CMFPlone.testing import PRODUCTS_CMFPLONE_INTEGRATION_TESTING
from Products.CMFPlone.tests import dummy
from zope.component import queryMultiAdapter
from zope.interface import Interface
from zope.interface import provider

import Missing
import unittest


# XXX Neither model.Schema not Interface seem to work for me.
@provider(IFormFieldProvider)
class ITwoImages(model.Schema):
    # class ITwoImages(Interface):
    image1 = NamedBlobImage(
        title="First image",
        required=False,
    )

    image2 = NamedBlobImage(
        title="Second image",
        required=False,
    )


class ImageScalesAdaptersRegisteredTest(unittest.TestCase):
    """Test portal actions control panel."""

    layer = PRODUCTS_CMFPLONE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        news_id = self.portal.invokeFactory(
            "News Item",
            id="news",
            title="News",
        )

        image_id = self.portal.invokeFactory(
            "Image",
            id="image",
            title="image",
            image=NamedImage(dummy.Image()),
        )

        self.image = self.portal[image_id]
        self.news = self.portal[news_id]

    def serialize(self, context, fieldname):
        for schema in iterSchemata(context):
            if fieldname in schema:
                field = schema.get(fieldname)
                break
        serializer = queryMultiAdapter(
            (field, context, self.request), IImageScalesFieldAdapter
        )
        if serializer:
            return serializer()
        return None

    def test_field_adapter_do_not_return_scales_for_fields_without_adapter(self):
        res = self.serialize(self.image, "title")
        self.assertEqual(res, None)

    def test_field_adapter_return_scales_for_fields_with_adapter(self):
        res = self.serialize(self.image, "image")
        self.assertNotEqual(res, None)
        self.assertEqual(len(res), 1)
        scales = res[0]
        self.assertEqual(scales["content-type"], "image/gif")
        self.assertIn("scales", scales)

    def test_field_adapter_do_not_return_scales_for_empty_fields_with_adapter(self):
        res = self.serialize(self.news, "image")
        self.assertEqual(res, None)

    def test_content_adapter_return_proper_scales(self):
        res = queryMultiAdapter((self.image, self.request), IImageScalesAdapter)()
        self.assertNotEqual(res, None)
        self.assertEqual(list(res.keys()), ["image"])
        self.assertEqual(len(res["image"]), 1)
        scales = res["image"][0]
        self.assertEqual(scales["content-type"], "image/gif")
        self.assertIn("scales", scales)

    def test_content_adapter_do_not_return_scales_if_empty_fields(self):
        res = queryMultiAdapter((self.news, self.request), IImageScalesAdapter)()
        self.assertEqual(res, {})

    def test_metadata_populated_with_scales(self):
        catalog = self.portal.portal_catalog
        news_brain = catalog(UID=self.news.UID())[0]
        image_brain = catalog(UID=self.image.UID())[0]

        self.assertEqual(news_brain.image_scales, Missing.Value)
        self.assertEqual(list(image_brain.image_scales.keys()), ["image"])
        self.assertEqual(len(image_brain.image_scales["image"]), 1)
        self.assertEqual(
            image_brain.image_scales["image"][0]["content-type"], "image/gif"
        )
        self.assertIn("scales", image_brain.image_scales["image"][0])

    def test_multiple_image_fields(self):
        fti = DexterityFTI(
            "multi",
            # XXX Neither of these two work: no fields are found in the
            # image scales adapter.
            # schema="Products.CMFPlone.image_scales.tests.ITwoImages",
            model_file="Products.CMFPlone.image_scales.tests:images.xml",
        )
        self.portal.portal_types._setObject("multi", fti)
        content_id = self.portal.invokeFactory(
            "multi",
            id="multi",
            title="Multi",
            image1=NamedImage(dummy.Image()),
            image2=NamedImage(dummy.Image()),
        )
        multi = self.portal[content_id]
        catalog = self.portal.portal_catalog
        brain = catalog(UID=multi.UID())[0]
        self.assertEqual(sorted(list(brain.image_scales.keys())), ["image1", "image2"])
