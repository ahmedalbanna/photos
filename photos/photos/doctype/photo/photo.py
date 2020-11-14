# -*- coding: utf-8 -*-
# Copyright (c) 2020, Gavin D'souza and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Photo(Document):
    def validate(self):
        # check if file type is supported
        pass

    def after_insert(self):
        # start processing etc, maybe via frappe.enqueue
        frappe.enqueue("photos.photos.doctype.photo.photo.process_photo", queue="long", photo=self)


def process_photo(photo: Photo):
    """Processes photo and searches Persons and Objects in them.

    TODO:
     - locating objects

    Args:
        photo (Photo): Photo document object
    """
    import json

    import face_recognition
    import numpy as np
    from frappe.core.doctype.file.file import get_local_image

    people = []
    image, filename, extn = get_local_image(
        frappe.db.get_value("File", photo.photo, "file_url")
    )
    img = np.asarray(image)
    boxes = face_recognition.face_locations(img, model='hog')
    encodings = face_recognition.face_encodings(img, boxes)

    for (encoding, location) in zip(encodings, boxes):
        roi = frappe.new_doc("ROI")
        roi.image = photo.photo
        roi.location = json.dumps(location)
        roi.encoding = json.dumps(encoding.tolist())
        roi.insert()
        people.append(roi.name)

    for x in people:
        photo.append("people", {"face": x})

    photo.number_of_times_processed += 1
    photo.is_processed = True
    photo.save()

    frappe.publish_realtime('refresh_photo', user=frappe.session.user)

    return photo
