# Demo objects for MEMO mode

Place photos in subfolders — folder name becomes the object name.

```
demo_objects/
  house_keys/
    angle1.jpg
    angle2.jpg
  pill_bottle/
    front.jpg
    side.jpg
  family_photo/
    photo.jpg
```

Import without the camera:

```bash
python collect_memo.py --folder demo_objects/
```

Evaluate matching accuracy:

```bash
python evaluate_memo.py --folder demo_objects/
```

When entering MEMO mode, vault may already contain demo objects if you ran:

```bash
python create_demo_images.py
python collect_memo.py --folder demo_objects/
```
