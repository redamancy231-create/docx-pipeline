# 数学公式测试

## 行内公式

质能方程 $E=mc^2$ 是物理学中最著名的公式之一。

勾股定理 $a^2 + b^2 = c^2$ 描述了直角三角形三边关系。

### \(...\) 分隔符（tex_math_single_backslash 新增能力）

行内公式也可用 \(a^2 + b^2 = c^2\) 表示。

## 块级公式

欧拉恒等式：

$$
e^{i\pi} + 1 = 0
$$

### \[...\] 分隔符（tex_math_single_backslash 新增能力）

\[
\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
\]

## 希腊字母和运算符

行内希腊字母：$\alpha + \beta = \gamma$，$\Delta x \to 0$，$\lambda$ 和 $\mu$。

求和与积分：

$$
\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}
$$

$$
\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$

## 分式和根号

行内分式 $\frac{a}{b}$ 和根号 $\sqrt{x^2 + y^2}$。

块级：

$$
\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$

## 矩阵

$$
\begin{pmatrix}
a & b \\
c & d
\end{pmatrix}
$$

## 极限

$$
\lim_{x \to \infty} \frac{1}{x} = 0
$$

## 多行公式

$$
\begin{aligned}
\nabla \cdot \mathbf{E} &= \frac{\rho}{\epsilon_0} \\
\nabla \cdot \mathbf{B} &= 0
\end{aligned}
$$
