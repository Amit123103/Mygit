# MyGit Security Subsystem & Cryptography Specification

## 1. Ed25519 Commit & Tag Signing

MyGit utilizes the **Ed25519 High-Speed High-Security Elliptic Curve Signature System** (Edwards-curve Digital Signature Algorithm over Curve25519).

### 1.1 Mathematical Properties
- **Security Level**: ~128 bits of security against quantum and classical attacks.
- **Key Sizes**: 32-byte public key, 64-byte private key.
- **Formulas**: Curve equation over prime field $\mathbb{F}_p$ where $p = 2^{255} - 19$:

$$-x^2 + y^2 = 1 - \frac{121665}{121666} x^2 y^2$$

### 1.2 Signature Flow
1. Generate PEM keypair using `mygit key generate`.
2. Private key saved locally in `.mygit/ed25519.priv` (chmod 600).
3. Commit text signed during `mygit commit --sign`.
4. Verification executed during `mygit log` or `mygit show`.

---

## 2. Entropy Secret Scanner & Heuristics

MyGit blocks accidental credential leaks before commit creation.

### 2.1 Shannon Entropy Algorithm
High-entropy strings (random API keys, tokens) are identified using Shannon entropy:

$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$

Where $P(x_i)$ is the probability of character $x_i$ appearing in token $X$.

- Threshold: Strings with length $\ge 24$ and $H(X) > 4.5$ trigger security warnings.

### 2.2 Heuristic Regex Rules:
- Private Keys (`BEGIN RSA/EC PRIVATE KEY`)
- AWS Access Keys (`AKIA[0-9A-Z]{16}`)
- GitHub Tokens (`ghp_[a-zA-Z0-9]{36}`)
- GitLab Tokens (`glpat-[a-zA-Z0-9\-]{20}`)
- Hugging Face Tokens (`hf_[a-zA-Z0-9]{34}`)
