---
weight: 5
title: "Backpropagation."
date: 2022-07-03T17:55:28+08:00
draft: true
math: true
author: "André"
description: "First blog post."
toc: false
tags: ["machine learning", "derivatives", "math", "backpropagation", "neural nets"]
categories: ["math", "general"]
---

# Notation 

Let us first recall some notation.

$$
  \gdef\norm#1{\left\lVert#1\right\rVert}
$$

{{< admonition type=note title="Definition" >}}
{{< raw >}}
{{< /raw >}}
{{< /admonition >}}

*Proof.*

{{< style "text-align: right;" >}}
$\blacksquare$
{{< /style >}}

{{< admonition type=note title="Definition" >}}
{{< raw >}}
Let $n \in \N$. We then define 
$$
\underline n \coloneqq \{1,2,3, \cdots, n \}.
$$
{{< /raw >}}
{{< /admonition >}}

{{< admonition type=note title="Definition" >}}
{{< raw >}}
Given a function
$$
f \colon \R^n \to \R^m,
$$
we denote by $f_i$ the $i$-th component of $f$, i.e. $f_i(x) = f(x)_i$, for all $x \in \R^n$ and $i \in \underline m$.
{{< /raw >}}
{{< /admonition >}}

# Derivatives

For a real function $f \colon \R \to \R$ the derivative $f'(a) \in \R$ satisfies
$$
  f'(a) = \lim_{x \to a} \frac{ f(x) - f(a) }{x-a} .
$$
Rewriting this gives
$$
  \lim_{x \to a} \frac{ f(x) - f(a) - f'(a)(x-a)}{x-a}  = 0.
$$
This justifies the following generalization.

{{< admonition type=note title="Definition (Total Derivative)" >}}
{{< raw >}}
Let $U \subseteq \R^n$ be an open subset and $f \colon U \to \R^m$. We say that $f$
is totally differentiable at $a \in U$ if there exists a linear transformation 
$$
  Df_a \colon \R^n \to \R^m
$$
such that
$$
  \lim_{x \to a} \frac{\norm{f(x) - f(a) - Df_a(x-a)}}{\norm{x-a}} = 0.
$$
{{< /raw >}}
{{< /admonition >}}
{{< admonition type=info title="NB">}}
With respect to the standard basis a linear transformation $\R^n \to \R^m$ can be identified with a $m\times n$-matrix.
{{< /admonition >}}


{{< admonition type=note title="Definition (Partial Derivative)" >}}
{{< raw >}}
Given $f\colon \R^n \to \R$, $i \in \underline n$ and $x \in \R^n$, we define 
$$
  \frac {\partial f}{\partial x_i}(x) \coloneqq \lim_{\varepsilon \to 0} \frac {f(x) - f(x + \varepsilon e_i )}{\varepsilon},
$$
provided that the limit exists. Note that $e_i$ is the $i$-th standard basis vector for $\R^n$.

If the limit exists for all $x \in \R^n$, we simply write 
$$
  \frac {\partial f}{\partial x_i} \colon \R^n \to \R : x \mapsto \frac {\partial f}{\partial x_i}(x).
$$
If the limit exists for all $x$ and $i$, we also define the Gradient of $f$ as the row-vector (or $1 \times n$ matrix)
$$
\nabla f = \left ( \frac {\partial f }{\partial x_i} \right )_{i=1}^n.
$$
{{< /raw >}}
{{< /admonition >}}


{{< admonition type=abstract title="Theorem 1" >}}
{{< raw >}}
Let $f \colon \R^n \to \R^m$ be a $C^1$-funciton, i.e. all partial derivatives exist and are continuous. Then
$$
  Df_a = \left ( \frac{\partial f_i}{\partial x_j}(a) \right)_{i,j} \in \R^{m \times n}.
$$
{{< /raw >}}
{{< /admonition >}}

{{< admonition type=abstract title="Theorem 2 (Chain Rule)" >}}
{{< raw >}}
{{< /raw >}}
{{< /admonition >}}

# Backpropagation

{{< admonition type=note title="Definition (Neural Net)" >}}
{{< raw >}}
A layer of a neural net is a function of the form 
$$
  f \colon \R^n \to \R^m : x \mapsto \sigma(Wx),
$$
where $\sigma \colon \R \to \R$ is a function and $W \in \R^{m \times n}$ a real matrix. 
By convention $\sigma(Wx)_i = \sigma((Wx)_i)$. This is called vectorization. 
<br>
{{< /raw >}}
{{< /admonition >}}

Such a layer is denoted by the quadrupel
$$
  f=(W,n,m, \sigma).
$$

Two layers $f_1=(W_1,n_1,m_1,\sigma_1)$ and $f_2=(W_2,n_2,m_2,\sigma_2)$ are called **compatible** if $f_2 \circ f_1$ is definied, i.e. if $m_1 = n_2$.

{{< admonition type=note title="Definition (Neural Net)" >}}
{{< raw >}}
A neural net is the composotion of a finite number of compatible layers. More precisely, let $(f_i)_{i=1}^N = (W_i,n_i,m_i,\sigma_i)_{i=1}^N$ be compatible layers. Then, the neural net $N$ is defined by 
$$
  N = f_N \circ f_{N-1} \circ \cdots \circ f_1 \colon \R^{n_1} \to \R^{m_N}.
$$
{{< /raw >}}
{{< /admonition >}}

Let $x \in \R^{n_1}$. Remembering, that all these variables depend on $x$, we define
{{< raw >}}
\begin{align*}
  a_0 & = x \in \R^{n_1} \\
  z_i &  = W_ia_{i-1} \in \R^{m_i} = \R^{n_{i+1}} & \qquad (1 \leq i \leq N) \\
  a_i & = \sigma(z_i) = f_i(a_{i-1}) \in \R^{m_i} = \R^{n_{i+1}} & \qquad (1 \leq i \leq N)
\end{align*}
{{< /raw >}}

This process is called feed-forward of $x$ and we see that $N(x) = N(a_0) = a_N$.
The elements $(a_i)_{i=0}^N$ are called the **activations** of the neural net.
The components of the single layers are sometimes called **neurons**.

The ultimate goal is to *train* the neural net on labelled training data.
The performance of a neural net is measured using so-called *cost* functions. In the following we will use the *mean-squared-error* cost-functions.


{{< admonition type=note title="Definition (MSE)" >}}
{{< raw >}}
Let $T=(x_i,y_i)_{i=1}^M \subseteq \R^{n_1} \times \R^{m_N}$ be the training data. We then define 
$$
  C(N,T) = \frac 1 M \sum_{i=1}^M C(N,x_i) = \frac 1 M \sum_{i=1}^M \norm{(x_i) - y_i}^2 .
$$
{{< /raw >}}
{{< /admonition >}}

The function $C(N,T)$ hence measures how well the function $N$ approximates the function
$$
 \sum_{i=1}^M y_i \cdot \chi_{x_i} \colon X \to \R^{m_N},
$$
where $X = \\{x_1,x_2, \cdots, x_M \\} \subseteq \R^{n_1}$ and $\chi_{x_i}$ is the point mass (indicator) on $\\{x_i\\}$.

{{< admonition type=question title="Exercise">}}
  Verify that 
  $$
    C(N,T) = \frac 1 M \norm{N_{\mid X} - \sum_i y_i \chi_{x_i}}^2,
  $$
  where $N_{\mid X}$ is the restriction of $N$ to $X$ and $\norm \cdot$ is the standard norm on $L^2(X)$.
{{< /admonition >}}

{{< admonition type=abstract title="Theorem 3 (Backpropagation)" >}}
{{< raw >}}
Let $(f_i)_{i=1}^N = (W_i,n_i,m_i,\sigma)$ be a neural net, with $\sigma \in C^1(\R)$. This defines $N = f_N \circ f_{N-1} \circ \cdots \circ f_1$. Let $(x,\hat x) \in \R^{n_1} \times \R^{m_N}$. Then 
$$
  \frac{\partial C(N,x,\hat x)}{\partial W^{(i)}_{k,l}}
$$
{{< /raw >}}
{{< /admonition >}}
*Proof.*
{{< raw >}}
We first look at the last layer.
\begin{align*}
    \frac{\partial C(N,x,\hat x)}{\partial W^{(N)}_{i,j}} 
    & = \sum_{l=1}^N \frac{\partial C(N, x, \hat x)}{\partial z^{(N)}_l} \frac{\partial z^{(N)}_l}{\partial W^{(N)}_{i,j}}
\end{align*}
Let us first compute the first factor in the sum:
\begin{align*}
  \frac{\partial C(N,x,\hat x)}{\partial z^{(N)}_l} & = \frac \partial {\partial z^{(N)}_l} \norm{\sigma(z^{(N)}) - \hat x}^2 \\
  & = 2 (\sigma(z^{(N)}_l) - \hat x_l) \sigma'(z^{(N)}_l) \\
  & = 2(a^{(N)}_l - \hat x_l) \sigma'(z^{(N)}_l)
\end{align*}
Note that we use that the squared norm function, denote it by 
$$
  n \colon \R^n \to \R : x \mapsto \norm x^2 = \sum_{i=1}^n x_i^2
$$
 has total derivative  
 $$
  D_x n = \nabla_x n = \left ( \frac {\partial n} {\partial x_1} \cdots \frac{\partial n}{\partial x_n} \right )_x = 2x^t.
 $$
{{< /raw >}}