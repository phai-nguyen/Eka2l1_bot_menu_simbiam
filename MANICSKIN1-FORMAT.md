# MANICSKIN1 format

A `.manicskin` file is a ZIP archive containing data-only Manic artwork and layout metadata.

## Required files

- `info.json`
- PNG files referenced by `info.json`

Optional files such as `preview.png` are allowed when they are PNG or JSON.

## Manifest

```json
{
  "format": 1,
  "id": "nokia-classic",
  "name": "Nokia Classic",
  "author": "Example",
  "version": "1.0",
  "representations": {
    "iphone": {
      "standard": {
        "portrait": {
          "mappingSize": { "width": 390, "height": 844 },
          "items": []
        },
        "landscape": {
          "mappingSize": { "width": 844, "height": 390 },
          "items": []
        }
      }
    }
  }
}
```

The `representations`, `mappingSize`, `items`, `asset`, `inputs`,
`thumbstick`, `frame`, and `extendedEdges` structures intentionally follow
the built-in native Manic skin schema already consumed by
`EKAManicControlsView`.

## Safety rules

MANICSKIN1 accepts only JSON and PNG content. It rejects executable content,
absolute paths, `..` traversal, backslash paths, oversized images, archives
larger than 30 MB, individual uncompressed files larger than 10 MB, and archives
with more than 128 entries.

The package controls artwork and layout data only. Symbian/N-Gage scancode
generation remains in the native `GameControlsView` path.
