import re
from typing import List, Dict, Union

class LatexParser:
    def __init__(self):
        # Regex patterns for different LaTeX elements
        self.patterns = {
            'section': r'\\section{([^}]*)}',
            'subsection': r'\\subsection{([^}]*)}',
            'paragraph': r'\\paragraph{([^}]*)}',
            # Handle both numbered and unnumbered environments
            'equation': r'\\begin\{equation\*?\}(.*?)\\end\{equation(?:\*)?\}',
            'align': r'\\begin\{align\*?\}(.*?)\\end\{align(?:\*)?\}',
            'equation_inline': r'\$([^$]*)\$',
            'citation': r'\\citep{([^}]*)}',
            'ref': r'\\ref{([^}]*)}',
            'comment': r'%([^\n]*)',
            'label': r'\\label{([^}]*)}',  # Add pattern for \label command
        }
        
    def parse(self, text: str) -> List[Dict[str, str]]:
        tokens = []
        current_pos = 0
        
        while current_pos < len(text):
            # Try to match each pattern at the current position
            match = None
            matched_type = None
            
            # Handle plain text until next LaTeX command
            next_command = re.search(r'\\|\$|%', text[current_pos:])
            if not next_command:
                # No more commands, add remaining text
                if current_pos < len(text):
                    remaining_text = text[current_pos:].strip()
                    if remaining_text:
                        tokens.append({
                            "type": "text",
                            "content": remaining_text
                        })
                break
                
            # Add text before the next command if it exists
            if next_command.start() > 0:
                plain_text = text[current_pos:current_pos + next_command.start()].strip()
                if plain_text:
                    tokens.append({
                        "type": "text",
                        "content": plain_text
                    })
                current_pos += next_command.start()
                continue
            
            # Try each pattern
            for pattern_type, pattern in self.patterns.items():
                match = re.match(pattern, text[current_pos:], re.DOTALL)
                if match:
                    matched_type = pattern_type
                    break
            
            if match:
                if matched_type == 'section':
                    tokens.append({
                        "type": "section",
                        "title": match.group(1).strip(),
                        "level": 1
                    })
                elif matched_type == 'subsection':
                    tokens.append({
                        "type": "section",
                        "title": match.group(1).strip(),
                        "level": 2
                    })
                elif matched_type == 'paragraph':
                    tokens.append({
                        "type": "section",
                        "title": match.group(1).strip(),
                        "level": 3
                    })
                elif matched_type in ['equation', 'align']:
                    # Check if it's a starred (unnumbered) environment
                    # env_name = text[current_pos:current_pos + match.end()].split('{')[1].split('}')[0]
                    # is_numbered = not env_name.endswith('*')
                    
                    tokens.append({
                        "type": "equation",
                        "content": match.group(1).strip(),
                        "display": "block",
                    })
                elif matched_type == 'equation_inline':
                    tokens.append({
                        "type": "equation",
                        "content": match.group(1).strip(),
                        "display": "inline"
                    })
                elif matched_type == 'citation':
                    tokens.append({
                        "type": "citation",
                        "id": match.group(1).strip()
                    })
                elif matched_type == 'ref':
                    tokens.append({
                        "type": "ref",
                        "id": match.group(1).strip()
                    })
                elif matched_type == 'comment':
                    tokens.append({
                        "type": "comment",
                        "content": match.group(1).strip()
                    })
                elif matched_type == 'label':
                    tokens.append({
                        "type": "label",
                        "id": match.group(1).strip()
                    })
                
                current_pos += match.end()
            else:
                # No match found, move forward one character
                current_pos += 1
        
        return tokens


text = """
\\section{Training}\nThis section describes the training regime for our models. \n\n%In order to speed up experimentation, our ablations are performed relative to a smaller base model described in detail in Section \\ref{sec:results}.\n\n\\subsection{Training Data and Batching}\nWe trained on the standard WMT 2014 English-German dataset consisting of about 4.5 million sentence pairs.  Sentences were encoded using byte-pair encoding \\citep{DBLP:journals/corr/BritzGLL17}, which has a shared source-target vocabulary of about 37000 tokens. For English-French, we used the significantly larger WMT 2014 English-French dataset consisting of 36M sentences and split tokens into a 32000 word-piece vocabulary \\citep{wu2016google}.  Sentence pairs were batched together by approximate sequence length.  Each training batch contained a set of sentence pairs containing approximately 25000 source tokens and 25000 target tokens.  \n\n\\subsection{Hardware and Schedule}\n\nWe trained our models on one machine with 8 NVIDIA P100 GPUs.  For our base models using the hyperparameters described throughout the paper, each training step took about 0.4 seconds.  We trained the base models for a total of 100,000 steps or 12 hours.  For our big models,(described on the bottom line of table \\ref{tab:variations}), step time was 1.0 seconds.  The big models were trained for 300,000 steps (3.5 days).\n\n\\subsection{Optimizer} We used the Adam optimizer~\\citep{kingma2014adam} with $\\\beta_1=0.9$, $\\\beta_2=0.98$ and $\\\epsilon=10^{-9}$.  We varied the learning rate over the course of training, according to the formula:\n\n\\begin{equation}\nlrate = \\dmodel^{-0.5} \\cdot\n  \\min({step\\_num}^{-0.5},\n    {step\\_num} \\cdot{warmup\\_steps}^{-1.5})\n\\end{equation}\n\nThis corresponds to increasing the learning rate linearly for the first $warmup\\_steps$ training steps, and decreasing it thereafter proportionally to the inverse square root of the step number.  We used $warmup\\_steps=4000$.\n\n\\subsection{Regularization} \\label{sec:reg}\n\nWe employ three types of regularization during training: \n\\paragraph{Residual Dropout} We apply dropout \\citep{srivastava2014dropout} to the output of each sub-layer, before it is added to the sub-layer input and normalized.   In addition, we apply dropout to the sums of the embeddings and the positional encodings in both the encoder and decoder stacks.  For the base model, we use a rate of $P_{drop}=0.1$.\n\n% \\paragraph{Attention Dropout} Query to key attentions are structurally similar to hidden-to-hidden weights in a feed-forward network, albeit across positions. The softmax activations yielding attention weights can then be seen as the analogue of hidden layer activations. A natural possibility is to extend dropout \\citep{srivastava2014dropout} to attention. We implement attention dropout by dropping out attention weights as,\n% \\begin{equation*}\n%   \\mathrm{Attention}(Q, K, V) = \\mathrm{dropout}(\\\mathrm{softmax}(\\\frac{QK^T}{\\\sqrt{d}}))V\n% \\end{equation*}\n% In addition to residual dropout, we found attention dropout to be beneficial for our parsing experiments.  \n\n%\\paragraph{Symbol Dropout} In the source and target embedding layers, we replace a random subset of the token ids with a sentinel id.  For the base model, we use a rate of $symbol\\_dropout\\_rate=0.1$.  Note that this applies only to the auto-regressive use of the target ids - not their use in the cross-entropy loss. \n\n%\\paragraph{Attention Dropout} Query to memory attentions are structurally similar to hidden-to-hidden weights in a feed-forward network, albeit across positions. The softmax activations yielding attention weights can then be seen as the analogue of hidden layer activations. A natural possibility is to extend dropout \\citep{srivastava2014dropout} to attentions. We implement attention dropout by dropping out attention weights as,\n%\\begin{align*}\n%   A(Q, K, V) = \\mathrm{dropout}(\\\mathrm{softmax}(\\\frac{QK^T}{\\\sqrt{d}}))V\n%\\end{align*}\n%As a result, the query will not be able to access the memory values at the dropped out position. In our experiments, we tried attention dropout rates of 0.2, and 0.3, and found it to work favorably for English-to-German translation.\n%$attention\\_dropout\\_rate=0.2$.\n\n\\paragraph{Label Smoothing} During training, we employed label smoothing of value $\\\epsilon_{ls}=0.1$ \\citep{DBLP:journals/corr/SzegedyVISW15}.  This hurts perplexity, as the model learns to be more unsure, but improves accuracy and BLEU score.\n\n \n
"""


# Example usage
parser = LatexParser()
parsed_tokens = parser.parse(text)

# print all equations
for token in parsed_tokens:
    if token["type"] == "citation": print(token)