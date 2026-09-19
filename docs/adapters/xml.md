# Constant-Memory XML Adapter (`XmlAdapter`)

`XmlAdapter` enables streaming through multi-gigabyte XML feeds while strictly guaranteeing flat **$O(1)$ RAM usage**.

---

## The XML Memory Challenge & Solution

Standard DOM and naive `iterparse` parsers leak memory when reading large XML files because root and ancestor elements accumulate references to child nodes. Even if you call `elem.clear()`, the parent node still stores pointers to all child nodes, eventually leading to Out-Of-Memory (OOM) crashes on 100 MB+ files.

`XmlAdapter` solves this by:
1. Pruning subtrees immediately after extraction.
2. Severing parent references (`parent.remove(elem)`) so Python's garbage collector instantly frees memory.
3. Operating strictly in bounded memory whether the file is 5 MB or 50 GB.

---

## Constructor Parameters

```python
adapters.XmlAdapter(
    source: Union[str, Path, BinaryIO, TextIO],
    target_tag: str,
    context_tags: Sequence[str] = (),
    strip_namespaces: bool = True,
    attr_prefix: str = "@",
    text_key: str = "#text",
)
```

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `source` | `str \| Path \| BinaryIO \| TextIO` | *Required* | File path or open stream. |
| `target_tag` | `str` | *Required* | Tag name of elements to extract and yield as records. |
| `context_tags` | `Sequence[str]` | `()` | Ancestor tags whose attributes are injected into child records. |
| `strip_namespaces`| `bool` | `True` | Automatically strips XML namespace URIs (e.g. `{http://...}item` $\rightarrow$ `item`). |
| `attr_prefix` | `str` | `"@"` | Prefix applied to XML attribute keys (e.g. `@id`). Set to `""` for no prefix. |
| `text_key` | `str` | `"#text"` | Dict key used for element inner text when the element also has attributes. |

---

## XML-to-Dictionary Transformation Rules

| XML Construct | Python Dictionary Representation |
| :--- | :--- |
| **Attributes** (`<item id="12">`) | `{"@id": "12"}` (or `{"id": "12"}` if `attr_prefix=""`) |
| **Simple Text Tag** (`<name>Keyboard</name>`) | `{"name": "Keyboard"}` |
| **Text with Attributes** (`<item sku="A1">Shoes</item>`) | `{"@sku": "A1", "#text": "Shoes"}` |
| **Repeated Sibling Tags** (`<tag>1</tag><tag>2</tag>`) | `{"tag": ["1", "2"]}` |
| **Nested Objects** (`<dimensions><w>10</w></dimensions>`) | `{"dimensions": {"w": "10"}}` |

---

## Examples

### 1. Extracting Catalog Items with Clean Namespaces

```xml
<catalog xmlns="http://ecommerce.org/schema">
    <item id="SKU-100">
        <title>Mechanical Keyboard</title>
        <price>129.99</price>
        <category>Electronics</category>
        <category>Gaming</category>
    </item>
</catalog>
```

```python
from pydantic import BaseModel, Field
from pydantic_stream_file import StreamValidator, adapters

class ItemModel(BaseModel):
    id: str = Field(alias="@id")
    title: str
    price: float
    category: list[str]

adapter = adapters.XmlAdapter(
    source="catalog.xml",
    target_tag="item",
    strip_namespaces=True
)

for item in StreamValidator(adapter, ItemModel):
    print(item.title, item.category)
```

---

### 2. Parent Context Extraction

In many feeds, vital metadata (e.g. `batch_id`, `warehouse_code`) lives on an ancestor element rather than repeated in each child:

```xml
<warehouse code="WH-EU" region="Europe">
    <batch number="BATCH-402">
        <order id="ORD-1">
            <total>250.00</total>
        </order>
        <order id="ORD-2">
            <total>49.99</total>
        </order>
    </batch>
</warehouse>
```

```python
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator, adapters

class OrderModel(BaseModel):
    id: str
    total: float
    warehouse_code: str
    batch_number: str

adapter = adapters.XmlAdapter(
    source="orders.xml",
    target_tag="order",
    context_tags=["warehouse", "batch"],
    attr_prefix="",
)

for order in StreamValidator(adapter, OrderModel):
    # Notice that warehouse_code and batch_number were injected automatically!
    print(order.id, order.total, order.warehouse_code, order.batch_number)
```
