## Papers

Store content like this
{ "type": "text", "content": "this model uses equation " },
{ "type": "ref", "id": "eq_123" },
{ "type": "text", "content": " which shows..." }

## Embeddings

for embeddings, store with the raw string (incl equations etc) embedded

## Equations

equations {
"id": string, // eq_123
"paper_id": string,  
 "content": string, // MathML/KaTeX representation
}

## Figures

figures {
"id": string, // fig_123
"paper_id": string,
"url": string, // image url
"caption": string, // figure caption
"alt_text": string // accessibility
}

## Tables

tables {
"id": string, // tab_123
"paper_id": string,
"data": Array<Array<string>>, // table contents
"caption": string,
"headers": string[] // column headers
}
