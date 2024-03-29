# E4E Weekly Presentations

# Setup Instructions
1. Install TexLive: https://www.tug.org/texlive/ (note: this might take a while)
2. Install VS Code
3. Clone `git@github.com:UCSD-E4E/weekly_presentations.git`
4. Open `weekly_presentations` in VS Code
5. Install the recommended extensions:
    - `james-yu.latex-workshop`

# Instructions for creating slides
1. Open the corresponding project file (`project_xxx.tex`) in VS Code.
2. For each frame, add the following
```
\begin{frame}{TITLE}
BODY
\end{frame}
```
where `TITLE` is the title of the slide, and `BODY` is the slide body.

Below are some slide examples:
```
\begin{frame}{Slide with bulleted list}
    \begin{itemize}
        \item ITEM 1
        \item ITEM 2
    \end{itemize}
\end{frame}

\begin{frame}{Slide with numbered list}
    \begin{enumerate}
        \item ITEM 1
        \item ITEM 2
    \end{enumerate}
\end{frame}

\begin{frame}{Slide with 2 columns}
    \begin{columns}
        \begin{column}{0.5\textwidth}
            COLUMN 1 BODY
        \end{column}
        \begin{column}{0.5\textwidth}
            COLUMN 2 BODY
        \end{column}
    \end{columns}
\end{frame}

\begin{frame}{Slide with centered image}
    \centering
    \includegraphics[height=0.7\textheight,width=0.7\textwidth,keepaspectratio]{picture.png}
\end{frame}
```
For the centered image, ensure that the image is one of the following formats: EPS, PDF, PNG, JPG.

3. VS Code should automatically compile the LaTeX document.  If not, open VS Code's Command Palatte and run `LaTeX Workshop: Build LaTeX project`.

# Viewing the final presentation
`.github/workflows/latex_build.yml` will automatically build and release each week's presentation.  The timing is controlled by the `on.schedule[0].cron` field.  The build artifact is a timestamped PDF build.  The GitHub release will always be the current date.  The presentation will also be deployed to GitHub pages at https://ucsd-e4e.github.io/weekly_presentations/e4e_weekly_presentation.pdf.