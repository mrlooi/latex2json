TRAINING_SECTION_TEXT = r"""
\section{Training}

This section describes the training regime for our models. 

%In order to speed up experimentation, our ablations are performed relative to a smaller base model described in detail in Section \ref{sec:results}.

\subsection{Training Data and Batching}
We trained on the standard WMT 2014 English-German dataset consisting of about 4.5 million sentence pairs.  Sentences were encoded using byte-pair encoding \citep{DBLP:journals/corr/BritzGLL17}, which has a shared source-target vocabulary of about 37000 tokens. For English-French, we used the significantly larger WMT 2014 English-French dataset consisting of 36M sentences and split tokens into a 32000 word-piece vocabulary \citep{wu2016google}.  Sentence pairs were batched together by approximate sequence length.  Each training batch contained a set of sentence pairs containing approximately 25000 source tokens and 25000 target tokens.  

\subsection{Hardware and Schedule}

We trained our models on one machine with 8 NVIDIA P100 GPUs.  For our base models using the hyperparameters described throughout the paper, each training step took about 0.4 seconds.  We trained the base models for a total of 100,000 steps or 12 hours.  For our big models,(described on the bottom line of table \ref{tab:variations}), step time was 1.0 seconds.  The big models were trained for 300,000 steps (3.5 days).

\subsection{Optimizer} We used the Adam optimizer~\citep{kingma2014adam} with $\beta_1=0.9$, $\beta_2=0.98$ and $\epsilon=10^{-9}$.  We varied the learning rate over the course of training, according to the formula:

\begin{equation}
lrate = \dmodel^{-0.5} \cdot
  \min({step\_num}^{-0.5},
    {step\_num} \cdot {warmup\_steps}^{-1.5})
\end{equation}

This corresponds to increasing the learning rate linearly for the first $warmup\_steps$ training steps, and decreasing it thereafter proportionally to the inverse square root of the step number.  We used $warmup\_steps=4000$.

\subsection{Regularization} \label{sec:reg}

We employ three types of regularization during training: 
\paragraph{Residual Dropout} We apply dropout \citep{srivastava2014dropout} to the output of each sub-layer, before it is added to the sub-layer input and normalized.   In addition, we apply dropout to the sums of the embeddings and the positional encodings in both the encoder and decoder stacks.  For the base model, we use a rate of $P_{drop}=0.1$.

% \paragraph{Attention Dropout} Query to key attentions are structurally similar to hidden-to-hidden weights in a feed-forward network, albeit across positions. The softmax activations yielding attention weights can then be seen as the analogue of hidden layer activations. A natural possibility is to extend dropout \citep{srivastava2014dropout} to attention. We implement attention dropout by dropping out attention weights as,
% \begin{equation*}
%   \mathrm{Attention}(Q, K, V) = \mathrm{dropout}(\mathrm{softmax}(\frac{QK^T}{\sqrt{d}}))V
% \end{equation*}
% In addition to residual dropout, we found attention dropout to be beneficial for our parsing experiments.  

%\paragraph{Symbol Dropout} In the source and target embedding layers, we replace a random subset of the token ids with a sentinel id.  For the base model, we use a rate of $symbol\_dropout\_rate=0.1$.  Note that this applies only to the auto-regressive use of the target ids - not their use in the cross-entropy loss. 

%\paragraph{Attention Dropout} Query to memory attentions are structurally similar to hidden-to-hidden weights in a feed-forward network, albeit across positions. The softmax activations yielding attention weights can then be seen as the analogue of hidden layer activations. A natural possibility is to extend dropout \citep{srivastava2014dropout} to attentions. We implement attention dropout by dropping out attention weights as,
%\begin{equation*}
%   A(Q, K, V) = \mathrm{dropout}(\mathrm{softmax}(\frac{QK^T}{\sqrt{d}}))V
%\end{equation*}
%As a result, the query will not be able to access the memory values at the dropped out position. In our experiments, we tried attention dropout rates of 0.2, and 0.3, and found it to work favorably for English-to-German translation.
%$attention\_dropout\_rate=0.2$.

\paragraph{Label Smoothing} During training, we employed label smoothing of value $\epsilon_{ls}=0.1$ \citep{DBLP:journals/corr/SzegedyVISW15}.  This hurts perplexity, as the model learns to be more unsure, but improves accuracy and BLEU score.

"""

RESULTS_SECTION_TEXT = r"""
\section{Results} \label{sec:results}
\subsection{Machine Translation}
\begin{table}[t]
\begin{center}
\caption{The Transformer achieves better BLEU scores than previous state-of-the-art models on the English-to-German and English-to-French newstest2014 tests at a fraction of the training cost.  }
\label{tab:wmt-results}
\vspace{-2mm}
%\scalebox{1.0}{
\begin{tabular}{lccccc}
\toprule
\multirow{2}{*}{\vspace{-2mm}Model} & \multicolumn{2}{c}{BLEU} & & \multicolumn{2}{c}{Training Cost (FLOPs)} \\
\cmidrule{2-3} \cmidrule{5-6} 
& EN-DE & EN-FR & & EN-DE & EN-FR \\ 
\hline
ByteNet \citep{NalBytenet2017} & 23.75 & & & &\\
Deep-Att + PosUnk \citep{DBLP:journals/corr/ZhouCWLX16} & & 39.2 & & & $1.0\cdot10^{20}$ \\
GNMT + RL \citep{wu2016google} & 24.6 & 39.92 & & $2.3\cdot10^{19}$  & $1.4\cdot10^{20}$\\
ConvS2S \citep{JonasFaceNet2017} & 25.16 & 40.46 & & $9.6\cdot10^{18}$ & $1.5\cdot10^{20}$\\
MoE \citep{shazeer2017outrageously} & 26.03 & 40.56 & & $2.0\cdot10^{19}$ & $1.2\cdot10^{20}$ \\
\hline
\rule{0pt}{2.0ex}Deep-Att + PosUnk Ensemble \citep{DBLP:journals/corr/ZhouCWLX16} & & 40.4 & & &
 $8.0\cdot10^{20}$ \\
GNMT + RL Ensemble \citep{wu2016google} & 26.30 & 41.16 & & $1.8\cdot10^{20}$  & $1.1\cdot10^{21}$\\
ConvS2S Ensemble \citep{JonasFaceNet2017} & 26.36 & \textbf{41.29} & & $7.7\cdot10^{19}$ & $1.2\cdot10^{21}$\\
\specialrule{1pt}{-1pt}{0pt}
\rule{0pt}{2.2ex}Transformer (base model) & 27.3 & 38.1 & & \multicolumn{2}{c}{\boldmath$3.3\cdot10^{18}$}\\
Transformer (big) & \textbf{28.4} & \textbf{41.8} & & \multicolumn{2}{c}{$2.3\cdot10^{19}$} \\
%\hline
%\specialrule{1pt}{-1pt}{0pt}
%\rule{0pt}{2.0ex}
\bottomrule
\end{tabular}
%}
\end{center}
\end{table}


On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table~\ref{tab:wmt-results}) outperforms the best previously reported models (including ensembles) by more than $2.0$ BLEU, establishing a new state-of-the-art BLEU score of $28.4$.  The configuration of this model is listed in the bottom line of Table~\ref{tab:variations}.  Training took $3.5$ days on $8$ P100 GPUs.  Even our base model surpasses all previously published models and ensembles, at a fraction of the training cost of any of the competitive models.

On the WMT 2014 English-to-French translation task, our big model achieves a BLEU score of $41.0$, outperforming all of the previously published single models, at less than $1/4$ the training cost of the previous state-of-the-art model. The Transformer (big) model trained for English-to-French used dropout rate $P_{drop}=0.1$, instead of $0.3$.

For the base models, we used a single model obtained by averaging the last 5 checkpoints, which were written at 10-minute intervals.  For the big models, we averaged the last 20 checkpoints. We used beam search with a beam size of $4$ and length penalty $\alpha=0.6$ \citep{wu2016google}.  These hyperparameters were chosen after experimentation on the development set.  We set the maximum output length during inference to input length + $50$, but terminate early when possible \citep{wu2016google}.

Table \ref{tab:wmt-results} summarizes our results and compares our translation quality and training costs to other model architectures from the literature.  We estimate the number of floating point operations used to train a model by multiplying the training time, the number of GPUs used, and an estimate of the sustained single-precision floating-point capacity of each GPU \footnote{We used values of 2.8, 3.7, 6.0 and 9.5 TFLOPS for K80, K40, M40 and P100, respectively.}.
%where we compare against the leading machine translation results in the literature. Even our smaller model, with number of parameters comparable to ConvS2S, outperforms all existing single models, and achieves results close to the best ensemble model.

\subsection{Model Variations}

\begin{table}[t]
\caption{Variations on the Transformer architecture. Unlisted values are identical to those of the base model.  All metrics are on the English-to-German translation development set, newstest2013.  Listed perplexities are per-wordpiece, according to our byte-pair encoding, and should not be compared to per-word perplexities.}
\label{tab:variations}
\begin{center}
\vspace{-2mm}
%\scalebox{1.0}{
\begin{tabular}{c|ccccccccc|ccc}
\hline\rule{0pt}{2.0ex}
 & \multirow{2}{*}{$N$} & \multirow{2}{*}{$\dmodel$} &
\multirow{2}{*}{$\dff$} & \multirow{2}{*}{$h$} & 
\multirow{2}{*}{$d_k$} & \multirow{2}{*}{$d_v$} & 
\multirow{2}{*}{$P_{drop}$} & \multirow{2}{*}{$\epsilon_{ls}$} &
train & PPL & BLEU & params \\
 & & & & & & & & & steps & (dev) & (dev) & $\times10^6$ \\
% & & & & & & & & & & & & \\
\hline\rule{0pt}{2.0ex}
base & 6 & 512 & 2048 & 8 & 64 & 64 & 0.1 & 0.1 & 100K & 4.92 & 25.8 & 65 \\
\hline\rule{0pt}{2.0ex}
\multirow{4}{*}{(A)}
& & & & 1 & 512 & 512 & & & & 5.29 & 24.9 &  \\
& & & & 4 & 128 & 128 & & & & 5.00 & 25.5 &  \\
& & & & 16 & 32 & 32 & & & & 4.91 & 25.8 &  \\
& & & & 32 & 16 & 16 & & & & 5.01 & 25.4 &  \\
\hline\rule{0pt}{2.0ex}
\multirow{2}{*}{(B)}
& & & & & 16 & & & & & 5.16 & 25.1 & 58 \\
& & & & & 32 & & & & & 5.01 & 25.4 & 60 \\
\hline\rule{0pt}{2.0ex}
\multirow{7}{*}{(C)}
& 2 & & & & & & & &            & 6.11 & 23.7 & 36 \\
& 4 & & & & & & & &            & 5.19 & 25.3 & 50 \\
& 8 & & & & & & & &            & 4.88 & 25.5 & 80 \\
& & 256 & & & 32 & 32 & & &    & 5.75 & 24.5 & 28 \\
& & 1024 & & & 128 & 128 & & & & 4.66 & 26.0 & 168 \\
& & & 1024 & & & & & &         & 5.12 & 25.4 & 53 \\
& & & 4096 & & & & & &         & 4.75 & 26.2 & 90 \\
\hline\rule{0pt}{2.0ex}
\multirow{4}{*}{(D)}
& & & & & & & 0.0 & & & 5.77 & 24.6 &  \\
& & & & & & & 0.2 & & & 4.95 & 25.5 &  \\
& & & & & & & & 0.0 & & 4.67 & 25.3 &  \\
& & & & & & & & 0.2 & & 5.47 & 25.7 &  \\
\hline\rule{0pt}{2.0ex}
(E) & & \multicolumn{7}{c}{positional embedding instead of sinusoids} & & 4.92 & 25.7 & \\
\hline\rule{0pt}{2.0ex}
big & 6 & 1024 & 4096 & 16 & & & 0.3 & & 300K & \textbf{4.33} & \textbf{26.4} & 213 \\
\hline
\end{tabular}
%}
\end{center}
\end{table}


%Table \ref{tab:ende-results}. Our base model for this task uses 6 attention layers, 512 hidden dim, 2048 filter dim, 8 attention heads with both attention and symbol dropout of 0.2 and 0.1 respectively. Increasing the filter size of our feed forward component to 8192 increases the BLEU score on En $\to$ De by $?$. For both the models, we use beam search decoding of size $?$ and length penalty with an alpha of $?$ \cite? \todo{Update results}

To evaluate the importance of different components of the Transformer, we varied our base model in different ways, measuring the change in performance on English-to-German translation on the development set, newstest2013. We used beam search as described in the previous section, but no checkpoint averaging.  We present these results in Table~\ref{tab:variations}.  

In Table~\ref{tab:variations} rows (A), we vary the number of attention heads and the attention key and value dimensions, keeping the amount of computation constant, as described in Section \ref{sec:multihead}. While single-head attention is 0.9 BLEU worse than the best setting, quality also drops off with too many heads.

In Table~\ref{tab:variations} rows (B), we observe that reducing the attention key size $d_k$ hurts model quality. This suggests that determining compatibility is not easy and that a more sophisticated compatibility function than dot product may be beneficial. We further observe in rows (C) and (D) that, as expected, bigger models are better, and dropout is very helpful in avoiding over-fitting.  In row (E) we replace our sinusoidal positional encoding with learned positional embeddings \citep{JonasFaceNet2017}, and observe nearly identical results to the base model.

%To evaluate the importance of different components of the Transformer, we use our base model to ablate on a single hyperparameter at each time and measure the change in performance on English$\to$German translation. Our variations in Table~\ref{tab:variations} show that the number of attention layers and attention heads is the most important architecture hyperparamter However, the we do not see performance gains beyond 6 layers, suggesting that we either don't have enough data to train a large model or we need to turn up regularization. We leave this exploration for future work. Among our regularizers, attention dropout has the most significant impact on performance.


%Increasing the width of our feed forward component helps both on log ppl and Accuracy \marginpar{Intuition?}
%Using dropout to regularize our models helps to prevent overfitting

\subsection{English Constituency Parsing}

\begin{table}[t]
\begin{center}
\caption{The Transformer generalizes well to English constituency parsing (Results are on Section 23 of WSJ)}
\label{tab:parsing-results}
\vspace{-2mm}
%\scalebox{1.0}{
\begin{tabular}{c|c|c}
\hline
{\bf Parser}  & {\bf Training} & {\bf WSJ 23 F1} \\ \hline
Vinyals \& Kaiser el al. (2014) \cite{KVparse15}
  & WSJ only, discriminative & 88.3 \\
Petrov et al. (2006) \cite{petrov-EtAl:2006:ACL}
  & WSJ only, discriminative & 90.4 \\
Zhu et al. (2013) \cite{zhu-EtAl:2013:ACL}
  & WSJ only, discriminative & 90.4   \\
Dyer et al. (2016) \cite{dyer-rnng:16}
  & WSJ only, discriminative & 91.7   \\
\specialrule{1pt}{-1pt}{0pt}
Transformer (4 layers)  &  WSJ only, discriminative & 91.3 \\
\specialrule{1pt}{-1pt}{0pt}   
Zhu et al. (2013) \cite{zhu-EtAl:2013:ACL}
  & semi-supervised & 91.3 \\
Huang \& Harper (2009) \cite{huang-harper:2009:EMNLP}
  & semi-supervised & 91.3 \\
McClosky et al. (2006) \cite{mcclosky-etAl:2006:NAACL}
  & semi-supervised & 92.1 \\
Vinyals \& Kaiser el al. (2014) \cite{KVparse15}
  & semi-supervised & 92.1 \\
\specialrule{1pt}{-1pt}{0pt}
Transformer (4 layers)  & semi-supervised & 92.7 \\
\specialrule{1pt}{-1pt}{0pt}   
Luong et al. (2015) \cite{multiseq2seq}
  & multi-task & 93.0   \\
Dyer et al. (2016) \cite{dyer-rnng:16}
  & generative & 93.3   \\
\hline
\end{tabular}
\end{center}
\end{table}

To evaluate if the Transformer can generalize to other tasks we performed experiments on English constituency parsing. This task presents specific challenges: the output is subject to strong structural constraints and is significantly longer than the input.
Furthermore, RNN sequence-to-sequence models have not been able to attain state-of-the-art results in small-data regimes \cite{KVparse15}.

We trained a 4-layer transformer with $d_{model} = 1024$ on the Wall Street Journal (WSJ) portion of the Penn Treebank \citep{marcus1993building}, about 40K training sentences. We also trained it in a semi-supervised setting, using the larger high-confidence and BerkleyParser corpora from with approximately 17M sentences \citep{KVparse15}. We used a vocabulary of 16K tokens for the WSJ only setting and a vocabulary of 32K tokens for the semi-supervised setting.

We performed only a small number of experiments to select the dropout, both attention and residual (section~\ref{sec:reg}), learning rates and beam size on the Section 22 development set, all other parameters remained unchanged from the English-to-German base translation model. During inference, we increased the maximum output length to input length + $300$. We used a beam size of $21$ and $\alpha=0.3$ for both WSJ only and the semi-supervised setting.

Our results in Table~\ref{tab:parsing-results} show that despite the lack of task-specific tuning our model performs surprisingly well, yielding better results than all previously reported models with the exception of the Recurrent Neural Network Grammar \cite{dyer-rnng:16}.

In contrast to RNN sequence-to-sequence models \citep{KVparse15}, the Transformer outperforms the BerkeleyParser \cite{petrov-EtAl:2006:ACL} even when training only on the WSJ training set of 40K sentences.

"""